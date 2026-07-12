<script setup>
/*
 * Folder-level tags + notes editor for the STL/3MF Library.
 *
 * Tags set here cascade DOWN to every file and subfolder beneath this folder
 * (copy-down model — see chat_docs/planning/LIBRARY_FOLDER_TAG_CASCADE_PLAN.md).
 * Notes are folder-local and never cascade. "Re-apply" forcefully pushes the
 * folder's current tags back onto the whole subtree (recovers from drift).
 *
 * Opened by right-clicking a folder in the tree (LibraryView owns the state).
 */
import { ref, watch, computed } from 'vue'
import APIService from '@/services/APIService'
import BaseModal from '@/components/BaseModal.vue'
import TagInput from '@/components/TagInput.vue'

const props = defineProps({
  show: { type: Boolean, required: true },
  folderId: { type: Number, default: null },
  folderName: { type: String, default: '' },
})

const emit = defineEmits(['close', 'saved'])

const loading = ref(false)
const saving = ref(false)
const error = ref(null)

const folderTags = ref([]) // selected tag objects { id, name, slug }
const notesDraft = ref('')
const originalTagIds = ref(new Set())

// Tags present when the modal opened but no longer selected — removing these
// will strip them from every file/subfolder below, so we confirm before saving.
const removedTags = computed(() =>
  [...originalTagIds.value].filter((id) => !folderTags.value.some((t) => t.id === id)),
)

watch(
  () => [props.show, props.folderId],
  async ([show, folderId]) => {
    if (!show || !folderId) return
    loading.value = true
    error.value = null
    folderTags.value = []
    notesDraft.value = ''
    try {
      const { data } = await APIService.getLibraryFolderMetadata(folderId)
      folderTags.value = data.tags || []
      notesDraft.value = data.notes || ''
      originalTagIds.value = new Set(folderTags.value.map((t) => t.id))
    } catch (err) {
      console.error('Failed to load folder metadata:', err)
      error.value = 'Failed to load folder tags and notes.'
    } finally {
      loading.value = false
    }
  },
  { immediate: true },
)

async function save() {
  if (!props.folderId || saving.value) return
  if (
    removedTags.value.length &&
    !confirm(
      'Removing a tag also removes it from every file and subfolder beneath this ' +
        'folder. Continue?',
    )
  )
    return
  saving.value = true
  error.value = null
  try {
    const { data } = await APIService.updateLibraryFolderMetadata(props.folderId, {
      tag_ids: folderTags.value.map((t) => t.id),
      notes: notesDraft.value,
    })
    emit('saved', data) // { affected_folders, affected_files, tags, notes, ... }
  } catch (err) {
    console.error('Failed to save folder metadata:', err)
    error.value = 'Failed to save. Please try again.'
  } finally {
    saving.value = false
  }
}

async function reapply() {
  if (!props.folderId || saving.value) return
  if (
    !confirm(
      "Re-apply this folder's tags to every file and subfolder beneath it? This " +
        'restores tags that may have been removed lower down.',
    )
  )
    return
  saving.value = true
  error.value = null
  try {
    // Persist any pending edits first so the push-down uses the latest tags.
    const { data } = await APIService.updateLibraryFolderMetadata(props.folderId, {
      tag_ids: folderTags.value.map((t) => t.id),
      notes: notesDraft.value,
    })
    const resync = await APIService.resyncLibraryFolder(props.folderId)
    emit('saved', { ...data, ...resync.data })
  } catch (err) {
    console.error('Failed to re-apply folder tags:', err)
    error.value = 'Failed to re-apply. Please try again.'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <BaseModal :show="show" :title="`Folder: ${folderName || 'Tags & Notes'}`" @close="emit('close')">
    <div v-if="loading" class="modal-state">Loading…</div>
    <div v-else-if="error" class="modal-state modal-error">{{ error }}</div>

    <template v-else>
      <h4 class="section-title">Tags</h4>
      <p class="cascade-hint">
        Tags set here apply to <strong>every file and subfolder</strong> beneath this folder.
        Files added by a future scan are tagged automatically.
      </p>
      <TagInput
        :model-value="folderTags"
        placeholder="Add folder tags… (type to search or create)"
        @update:model-value="folderTags = $event"
      />
      <p v-if="removedTags.length" class="removal-warning">
        Saving will remove {{ removedTags.length }} tag{{ removedTags.length === 1 ? '' : 's' }}
        from all files and subfolders below.
      </p>

      <h4 class="section-title">Notes</h4>
      <p class="cascade-hint">Folder notes are searchable but stay on the folder — they don't cascade.</p>
      <textarea
        v-model="notesDraft"
        class="notes-input"
        rows="3"
        placeholder="Notes about this folder… (searchable)"
        spellcheck="true"
      ></textarea>
    </template>

    <template #footer>
      <button class="btn btn-secondary" @click="emit('close')">Cancel</button>
      <button
        class="btn btn-outline"
        :disabled="loading || saving"
        title="Push this folder's tags onto everything beneath it"
        @click="reapply"
      >
        Re-apply to all below
      </button>
      <button class="btn btn-primary" :disabled="loading || saving" @click="save">
        {{ saving ? 'Saving…' : 'Save' }}
      </button>
    </template>
  </BaseModal>
</template>

<style scoped>
.modal-state {
  padding: 24px 0;
  text-align: center;
  color: var(--color-text-muted, var(--color-text));
}

.modal-error {
  color: var(--color-text);
}

.section-title {
  margin: 16px 0 6px;
  color: var(--color-heading);
}

.section-title:first-child {
  margin-top: 0;
}

.cascade-hint {
  margin: 0 0 8px;
  font-size: 0.85rem;
  color: var(--color-text);
  opacity: 0.75;
}

.removal-warning {
  margin: 8px 0 0;
  padding: 8px 12px;
  background-color: rgba(245, 158, 11, 0.1);
  border: 1px solid rgba(245, 158, 11, 0.3);
  border-radius: 4px;
  color: var(--color-text);
  font-size: 0.85rem;
}

.notes-input {
  width: 100%;
  padding: 8px 12px;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  box-sizing: border-box;
  background-color: var(--color-background);
  color: var(--color-text);
  font-size: 1rem;
  font-family: inherit;
  resize: vertical;
}

.notes-input:focus {
  outline: none;
  border-color: var(--color-blue);
  box-shadow: 0 0 0 2px rgba(13, 110, 253, 0.15);
}
</style>
