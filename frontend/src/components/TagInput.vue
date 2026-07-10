<script setup>
/*
 * Multi-select tag editor. Thin wrapper over vue-multiselect (same library +
 * "type to filter, Enter to create" pattern the Inventory forms use for Part
 * Type / Location), so tagging feels identical everywhere. `@tag` creates a new
 * tag via the API (idempotent server-side) and selects it.
 *
 * v-model is an array of tag objects ({ id, name, slug }).
 */
import { ref, computed, onMounted } from 'vue'
import Multiselect from 'vue-multiselect'
import 'vue-multiselect/dist/vue-multiselect.css'
import APIService from '@/services/APIService'

const props = defineProps({
  modelValue: { type: Array, default: () => [] },
  placeholder: { type: String, default: 'Add tags…' },
})
const emit = defineEmits(['update:modelValue'])

const options = ref([])

const selected = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value),
})

onMounted(loadTags)

async function loadTags() {
  try {
    const response = await APIService.getTags()
    options.value = response.data
  } catch (err) {
    console.error('Failed to load tags:', err)
  }
}

async function onCreate(name) {
  try {
    const { data: tag } = await APIService.createTag(name)
    if (!options.value.some((t) => t.id === tag.id)) options.value.push(tag)
    if (!props.modelValue.some((t) => t.id === tag.id)) {
      emit('update:modelValue', [...props.modelValue, tag])
    }
  } catch (err) {
    console.error('Failed to create tag:', err)
  }
}
</script>

<template>
  <Multiselect
    v-model="selected"
    :options="options"
    :multiple="true"
    :taggable="true"
    :close-on-select="false"
    label="name"
    track-by="id"
    :placeholder="placeholder"
    tag-placeholder="Press enter to create tag"
    @tag="onCreate"
  />
</template>
