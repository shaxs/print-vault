"""
Tests for the chunked, time-budgeted tracker thumbnail regeneration job
(services/tracker_thumbnail_jobs). This replaced the single whole-tracker task
that blew the Django-Q worker timeout on large trackers, so the key behaviours
are: eligibility, stale-auto-image cleanup, progress accounting, finalization,
and time-budgeted re-enqueue. Rendering itself is mocked — that's covered by
test_stl_thumbnail_service.
"""
from datetime import timedelta
from unittest import mock

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from inventory.models import TrackerThumbnailJob, TrackerFileImage
from inventory.services import tracker_thumbnail_jobs as jobs
from inventory.tests.factories import (
    TrackerFactory,
    TrackerFileFactory,
    TrackerFileImageFactory,
)

GEN = 'inventory.services.stl_thumbnail_service.generate_auto_thumbnail'


@pytest.mark.django_db
class TestStart:
    def test_creates_job_and_enqueues_orchestrator(self):
        tracker = TrackerFactory()
        with mock.patch.object(jobs, 'async_task') as m:
            job = jobs.start_tracker_thumbnail_regeneration(tracker, include_linked=True)
        assert job is not None
        assert job.status == 'pending'
        assert job.include_linked is True
        m.assert_called_once_with(
            'inventory.tasks.run_tracker_thumbnail_regeneration_task', job.pk
        )

    def test_refuses_when_job_already_active(self):
        tracker = TrackerFactory()
        TrackerThumbnailJob.objects.create(tracker=tracker, status='running')
        with mock.patch.object(jobs, 'async_task') as m:
            job = jobs.start_tracker_thumbnail_regeneration(tracker)
        assert job is None
        m.assert_not_called()

    def test_displaces_stale_job(self):
        tracker = TrackerFactory()
        stale = TrackerThumbnailJob.objects.create(tracker=tracker, status='running')
        # created_at is auto_now_add — backdate it past the stale threshold.
        TrackerThumbnailJob.objects.filter(pk=stale.pk).update(
            created_at=timezone.now() - timedelta(hours=jobs.STALE_JOB_AGE_HOURS + 1)
        )
        with mock.patch.object(jobs, 'async_task'):
            job = jobs.start_tracker_thumbnail_regeneration(tracker)
        assert job is not None
        stale.refresh_from_db()
        assert stale.status == 'error'


@pytest.mark.django_db
class TestRunRegeneration:
    def test_queues_eligible_and_deletes_stale_auto_images(self):
        tracker = TrackerFactory()
        f1 = TrackerFileFactory(tracker=tracker, storage_type='local', filename='a.stl')
        TrackerFileFactory(tracker=tracker, storage_type='local', filename='b.3mf')
        # Manual image -> excluded (never overwrite a manual upload).
        manual = TrackerFileFactory(tracker=tracker, storage_type='local', filename='c.stl')
        TrackerFileImageFactory(tracker_file=manual, is_auto_generated=False)
        # Non-STL/3MF -> excluded.
        TrackerFileFactory(tracker=tracker, storage_type='local', filename='d.png')
        # Stale auto image on f1 -> should be deleted so the render isn't a no-op.
        stale_img = TrackerFileImageFactory(tracker_file=f1, is_auto_generated=True)

        job = TrackerThumbnailJob.objects.create(tracker=tracker)
        with mock.patch.object(jobs, 'async_task') as m:
            jobs.run_regeneration(job.pk)

        job.refresh_from_db()
        assert job.status == 'running'
        assert job.files_queued == 2  # f1 (.stl) + b.3mf
        assert not TrackerFileImage.objects.filter(pk=stale_img.pk).exists()
        assert m.call_count == 1  # a single chunk (2 files < CHUNK_SIZE)

    def test_finalizes_success_when_no_eligible_files(self):
        tracker = TrackerFactory()
        job = TrackerThumbnailJob.objects.create(tracker=tracker)
        with mock.patch.object(jobs, 'async_task') as m:
            jobs.run_regeneration(job.pk)
        job.refresh_from_db()
        assert job.status == 'success'
        assert job.files_queued == 0
        m.assert_not_called()


@pytest.mark.django_db
class TestProcessChunk:
    def test_renders_bumps_progress_and_finalizes(self):
        tracker = TrackerFactory()
        f1 = TrackerFileFactory(tracker=tracker, storage_type='local', filename='a.stl')
        f2 = TrackerFileFactory(tracker=tracker, storage_type='local', filename='b.stl')
        job = TrackerThumbnailJob.objects.create(tracker=tracker, status='running', files_queued=2)

        with mock.patch(GEN, return_value=object()) as gen:
            jobs.process_chunk(job.pk, [f1.pk, f2.pk])

        job.refresh_from_db()
        assert job.files_processed == 2
        assert job.files_generated == 2
        assert job.status == 'success'
        assert job.finished_at is not None
        assert gen.call_count == 2

    def test_time_budget_reenqueues_remainder(self):
        tracker = TrackerFactory()
        f1 = TrackerFileFactory(tracker=tracker, storage_type='local', filename='a.stl')
        f2 = TrackerFileFactory(tracker=tracker, storage_type='local', filename='b.stl')
        job = TrackerThumbnailJob.objects.create(tracker=tracker, status='running', files_queued=2)

        with mock.patch.object(jobs, 'CHUNK_TIME_BUDGET_SECONDS', 0), \
             mock.patch.object(jobs, 'async_task') as m, \
             mock.patch(GEN, return_value=object()):
            jobs.process_chunk(job.pk, [f1.pk, f2.pk])

        job.refresh_from_db()
        assert job.files_processed == 1  # only the first file before the budget tripped
        assert job.status == 'running'   # not finalized — work remains
        m.assert_called_once_with(
            'inventory.tasks.process_tracker_thumbnail_chunk_task', job.pk, [f2.pk]
        )

    def test_per_file_failure_is_counted_not_fatal(self):
        tracker = TrackerFactory()
        f1 = TrackerFileFactory(tracker=tracker, storage_type='local', filename='a.stl')
        job = TrackerThumbnailJob.objects.create(tracker=tracker, status='running', files_queued=1)

        with mock.patch(GEN, side_effect=RuntimeError('boom')):
            jobs.process_chunk(job.pk, [f1.pk])

        job.refresh_from_db()
        assert job.files_processed == 1
        assert job.files_generated == 0
        assert job.status == 'success'


@pytest.mark.django_db
class TestJobStatusEndpoint:
    def test_active_and_tracker_filters(self):
        client = APIClient()
        t1 = TrackerFactory()
        t2 = TrackerFactory()
        running = TrackerThumbnailJob.objects.create(tracker=t1, status='running')
        done = TrackerThumbnailJob.objects.create(tracker=t1, status='success')
        other = TrackerThumbnailJob.objects.create(tracker=t2, status='running')

        resp = client.get(f'/api/tracker-thumbnail-jobs/?tracker={t1.pk}&active=true')
        assert resp.status_code == 200
        rows = resp.data['results'] if isinstance(resp.data, dict) and 'results' in resp.data else resp.data
        ids = [j['id'] for j in rows]
        assert running.pk in ids
        assert done.pk not in ids   # not active
        assert other.pk not in ids  # different tracker
