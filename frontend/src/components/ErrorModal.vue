<script setup>
defineProps({
  show: { type: Boolean, required: true },
  title: { type: String, default: 'An Error Occurred' },
  message: { type: String, default: 'Something went wrong. Please try again.' },
})

const emit = defineEmits(['close'])
</script>

<template>
  <div v-if="show" class="modal-overlay" @click="emit('close')">
    <div class="modal-form" @click.stop>
      <h3 class="error-title">{{ title }}</h3>
      <p>{{ message }}</p>
      <div class="form-actions">
        <button @click="emit('close')" type="button" class="btn btn-secondary">Close</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(0, 0, 0, 0.8);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}
.modal-form {
  background-color: var(--color-background-soft);
  padding: 20px;
  border-radius: 8px;
  width: 90%;
  max-width: 500px;
  border-left: 5px solid var(--color-red);
}
.error-title {
  color: var(--color-red);
}
.modal-form h3 {
  margin-bottom: 20px;
}
.modal-form p {
  margin-bottom: 20px;
}
</style>
