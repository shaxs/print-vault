<template>
  <svg
    class="spinner"
    width="24px"
    height="24px"
    viewBox="0 0 24 24"
    xmlns="http://www.w3.org/2000/svg"
  >
    <circle
      class="path"
      cx="12"
      cy="12"
      r="10"
      fill="none"
      stroke-width="4"
      stroke="currentColor"
    />
  </svg>
</template>

<style scoped>
.spinner {
  animation: rotate 2s linear infinite;
  width: 1em; /* Scale with font size */
  height: 1em;
  vertical-align: middle;
}

.path {
  stroke-linecap: round;
  animation: dash 1.5s ease-in-out infinite;
  stroke-dasharray: 90, 150;
  stroke-dashoffset: 0;
}

@keyframes rotate {
  100% {
    transform: rotate(360deg);
  }
}

@keyframes dash {
  0% {
    stroke-dasharray: 1, 200;
    stroke-dashoffset: 0;
  }
  50% {
    stroke-dasharray: 89, 200;
    stroke-dashoffset: -35px;
  }
  100% {
    stroke-dasharray: 89, 200;
    stroke-dashoffset: -124px;
  }
}
</style>
