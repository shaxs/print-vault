/**
 * Unit tests for ModelViewer.vue
 *
 * WebGLRenderer needs a real GPU context that doesn't exist in happy-dom, and
 * STLLoader/3MFLoader parse real binary formats we don't need to re-test here —
 * both are mocked. Everything else (Scene, Box3, Vector3, Color, Mesh, camera
 * framing math) uses the real `three` package so frameObject()'s actual logic
 * is exercised, not a re-implementation of it.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import * as THREE from 'three'
import ModelViewer from '@/components/ModelViewer.vue'

vi.mock('three', async (importOriginal) => {
  const actual = await importOriginal()
  return {
    ...actual,
    WebGLRenderer: vi.fn().mockImplementation(() => ({
      domElement: document.createElement('canvas'),
      setSize: vi.fn(),
      setPixelRatio: vi.fn(),
      render: vi.fn(),
      dispose: vi.fn(),
      forceContextLoss: vi.fn(),
    })),
  }
})

const stlParseMock = vi.fn(() => new THREE.BufferGeometry())
vi.mock('three/addons/loaders/STLLoader.js', () => ({
  STLLoader: vi.fn().mockImplementation(() => ({ parse: stlParseMock })),
}))

const threeMFParseMock = vi.fn(() => new THREE.Group())
vi.mock('three/addons/loaders/3MFLoader.js', () => ({
  ThreeMFLoader: vi.fn().mockImplementation(() => ({ parse: threeMFParseMock })),
}))

vi.mock('three/addons/controls/OrbitControls.js', () => ({
  OrbitControls: vi.fn().mockImplementation(() => ({
    enableDamping: false,
    dampingFactor: 0,
    target: new THREE.Vector3(),
    update: vi.fn(),
    dispose: vi.fn(),
  })),
}))

beforeEach(() => {
  vi.stubGlobal('requestAnimationFrame', vi.fn(() => 1))
  vi.stubGlobal('cancelAnimationFrame', vi.fn())
  stlParseMock.mockClear()
  threeMFParseMock.mockClear()
})

afterEach(() => {
  vi.unstubAllGlobals()
})

function stubFetch(ok = true) {
  vi.stubGlobal(
    'fetch',
    vi.fn().mockResolvedValue({
      ok,
      status: ok ? 200 : 404,
      arrayBuffer: async () => new ArrayBuffer(8),
    }),
  )
}

describe('ModelViewer', () => {
  it('shows a loading overlay while the model is being fetched', async () => {
    let resolveFetch
    vi.stubGlobal(
      'fetch',
      vi.fn(() => new Promise((resolve) => { resolveFetch = resolve })),
    )

    const wrapper = mount(ModelViewer, { props: { url: '/media/part.stl' } })
    await wrapper.vm.$nextTick()
    await Promise.resolve()

    expect(wrapper.text()).toContain('Loading model...')

    resolveFetch({ ok: true, arrayBuffer: async () => new ArrayBuffer(8) })
  })

  it('uses STLLoader for a .stl URL', async () => {
    stubFetch()
    mount(ModelViewer, { props: { url: '/media/part.stl' } })
    await new Promise((r) => setTimeout(r, 0))
    await new Promise((r) => setTimeout(r, 0))

    expect(stlParseMock).toHaveBeenCalled()
    expect(threeMFParseMock).not.toHaveBeenCalled()
  })

  it('uses ThreeMFLoader for a .3mf URL', async () => {
    stubFetch()
    mount(ModelViewer, { props: { url: '/media/part.3mf' } })
    await new Promise((r) => setTimeout(r, 0))
    await new Promise((r) => setTimeout(r, 0))

    expect(threeMFParseMock).toHaveBeenCalled()
    expect(stlParseMock).not.toHaveBeenCalled()
  })

  it('shows an error overlay when the fetch fails', async () => {
    stubFetch(false)
    const wrapper = mount(ModelViewer, { props: { url: '/media/missing.stl' } })
    await new Promise((r) => setTimeout(r, 0))
    await new Promise((r) => setTimeout(r, 0))
    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain('Failed to load model')
  })

  it('reloads the model when the url prop changes', async () => {
    stubFetch()
    const wrapper = mount(ModelViewer, { props: { url: '/media/part.stl' } })
    await new Promise((r) => setTimeout(r, 0))
    await new Promise((r) => setTimeout(r, 0))

    await wrapper.setProps({ url: '/media/other.3mf' })
    await new Promise((r) => setTimeout(r, 0))
    await new Promise((r) => setTimeout(r, 0))

    expect(threeMFParseMock).toHaveBeenCalled()
  })
})
