<script setup>
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue'
import * as THREE from 'three'
import { STLLoader } from 'three/addons/loaders/STLLoader.js'
import { ThreeMFLoader } from 'three/addons/loaders/3MFLoader.js'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'

const props = defineProps({
  url: { type: String, required: true },
  color: { type: String, default: '' },
})

const containerRef = ref(null)
const loading = ref(true)
const error = ref(null)

let renderer, scene, camera, controls, animationId

function init(container) {
  const width = container.clientWidth
  const height = container.clientHeight || 300

  scene = new THREE.Scene()
  scene.background = new THREE.Color(0x1a1a2e)

  camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 10000)

  renderer = new THREE.WebGLRenderer({ antialias: true })
  renderer.setSize(width, height)
  renderer.setPixelRatio(window.devicePixelRatio)
  container.appendChild(renderer.domElement)

  const ambientLight = new THREE.AmbientLight(0xffffff, 0.6)
  scene.add(ambientLight)

  const dirLight1 = new THREE.DirectionalLight(0xffffff, 0.8)
  dirLight1.position.set(1, 1, 1)
  scene.add(dirLight1)

  const dirLight2 = new THREE.DirectionalLight(0xffffff, 0.4)
  dirLight2.position.set(-1, -0.5, -1)
  scene.add(dirLight2)

  controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true
  controls.dampingFactor = 0.1

  const gridHelper = new THREE.GridHelper(200, 20, 0x444466, 0x333355)
  scene.add(gridHelper)
}

function getExtension(url) {
  return url.split('?')[0].split('.').pop().toLowerCase()
}

function frameObject(object) {
  const box = new THREE.Box3().setFromObject(object)
  const center = new THREE.Vector3()
  const size = new THREE.Vector3()
  box.getCenter(center)
  box.getSize(size)

  object.position.sub(center)
  object.position.y += size.y / 2

  scene.add(object)

  const distance = Math.max(size.x, size.y, size.z) * 2
  camera.position.set(distance, distance * 0.8, distance)
  camera.lookAt(0, size.y / 4, 0)
  controls.target.set(0, size.y / 4, 0)
  controls.update()
}

async function loadModel(url) {
  loading.value = true
  error.value = null

  try {
    const response = await fetch(url)
    if (!response.ok) throw new Error(`HTTP ${response.status}`)
    const buffer = await response.arrayBuffer()
    const ext = getExtension(url)

    if (ext === '3mf') {
      const loader = new ThreeMFLoader()
      const group = loader.parse(buffer)
      frameObject(group)
    } else {
      const loader = new STLLoader()
      const geometry = loader.parse(buffer)
      const hex = props.color && props.color.startsWith('#') ? props.color : '#94a3b8'
      const material = new THREE.MeshPhongMaterial({
        color: new THREE.Color(hex),
        specular: 0x222222,
        shininess: 40,
      })
      frameObject(new THREE.Mesh(geometry, material))
    }

    loading.value = false
  } catch (err) {
    console.error('Model load error:', err)
    error.value = 'Failed to load model'
    loading.value = false
  }
}

function clearScene() {
  const toRemove = []
  scene.traverse((obj) => {
    if (obj.isMesh || obj.isGroup) toRemove.push(obj)
  })
  toRemove.forEach((obj) => {
    if (obj.isMesh) {
      obj.geometry.dispose()
      if (Array.isArray(obj.material)) {
        obj.material.forEach((m) => m.dispose())
      } else {
        obj.material.dispose()
      }
    }
    scene.remove(obj)
  })
}

function animate() {
  animationId = requestAnimationFrame(animate)
  controls.update()
  renderer.render(scene, camera)
}

function handleResize() {
  if (!containerRef.value || !renderer) return
  const width = containerRef.value.clientWidth
  const height = containerRef.value.clientHeight || 300
  camera.aspect = width / height
  camera.updateProjectionMatrix()
  renderer.setSize(width, height)
}

onMounted(async () => {
  await nextTick()
  if (containerRef.value) {
    init(containerRef.value)
    loadModel(props.url)
    animate()
    window.addEventListener('resize', handleResize)
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  if (animationId) cancelAnimationFrame(animationId)
  if (controls) controls.dispose()
  if (renderer) {
    renderer.dispose()
    renderer.forceContextLoss()
  }
})

watch(
  () => props.url,
  (newUrl) => {
    clearScene()
    loadModel(newUrl)
  },
)

watch(
  () => props.color,
  (newColor) => {
    if (!newColor || !newColor.startsWith('#')) return
    const color = new THREE.Color(newColor)
    scene.traverse((obj) => {
      if (obj.isMesh && obj.material && !Array.isArray(obj.material)) {
        obj.material.color.copy(color)
      }
    })
  },
)
</script>

<template>
  <div class="model-viewer-wrapper">
    <div v-if="loading" class="model-overlay">Loading model...</div>
    <div v-if="error" class="model-overlay model-error">{{ error }}</div>
    <div ref="containerRef" class="model-canvas-container"></div>
  </div>
</template>

<style scoped>
.model-viewer-wrapper {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 300px;
}
.model-canvas-container {
  width: 100%;
  height: 100%;
  min-height: 300px;
}
.model-overlay {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  color: var(--color-text);
  font-size: 1rem;
  z-index: 10;
  background: rgba(0, 0, 0, 0.6);
  padding: 8px 16px;
  border-radius: 6px;
}
.model-error {
  color: #ef4444;
}
</style>
