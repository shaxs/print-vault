<template>
  <div class="about-tab-container">
    <div class="content-header">
      <h3>About Print Vault</h3>
    </div>

    <!-- Update Available Notification -->
    <div
      v-if="updateInfo.update_available && !updateDismissed"
      class="update-notification alert-info"
    >
      <div class="alert-content">
        <span class="alert-title">Update Available - v{{ updateInfo.latest_version }}</span>
        <span class="alert-message"
          >You're currently on {{ updateInfo.current_version }}. A new version is now
          available.</span
        >
        <div class="alert-actions">
          <a
            :href="updateInfo.release_url"
            target="_blank"
            rel="noopener noreferrer"
            class="update-link"
          >
            View Release Notes →
          </a>
        </div>
      </div>
      <button @click="dismissUpdate" class="btn-dismiss" title="Dismiss notification">✕</button>
    </div>

    <!-- Version Information Section -->
    <div class="info-section">
      <h4>Version Information</h4>

      <div v-if="loading" class="loading">
        <p>Loading version information...</p>
      </div>

      <div v-else-if="error" class="error">
        <p>Failed to load version information: {{ error }}</p>
        <button @click="fetchVersion" class="retry-button">Retry</button>
      </div>

      <div v-else>
        <!-- Version Mismatch Warning -->
        <div v-if="versionMismatch" class="version-mismatch alert-warning">
          <div class="alert-content">
            <span class="alert-title">Version Mismatch Detected</span>
            <span class="alert-message"
              >Frontend ({{ frontendVersion }}) and Backend ({{ versionInfo.version }}) versions
              don't match. Please rebuild your containers or clear your browser cache.</span
            >
          </div>
        </div>

        <div class="version-grid">
          <div class="version-item">
            <span class="label">Frontend Version:</span>
            <span class="value">{{ frontendVersion }}</span>
          </div>

          <div class="version-item">
            <span class="label">Backend Version:</span>
            <span class="value">{{ versionInfo.version || 'Unknown' }}</span>
          </div>

          <div class="version-item">
            <span class="label">Git Commit:</span>
            <span class="value monospace">{{ versionInfo.commit || 'unknown' }}</span>
          </div>

          <div class="version-item">
            <span class="label">Git Branch:</span>
            <span class="value monospace">{{ versionInfo.branch || 'unknown' }}</span>
          </div>

          <div class="version-item">
            <span class="label">Python Version:</span>
            <span class="value">{{ versionInfo.python_version || 'Unknown' }}</span>
          </div>

          <div class="version-item">
            <span class="label">Django Version:</span>
            <span class="value">{{ versionInfo.django_version || 'Unknown' }}</span>
          </div>

          <div class="version-item">
            <span class="label">Build Time:</span>
            <span class="value">{{ formatDateTime(versionInfo.build_time) }}</span>
          </div>
        </div>
      </div>

      <button @click="copyVersionInfo" class="copy-button">
        {{ copied ? '✓ Copied!' : 'Copy Version Info' }}
      </button>
    </div>

    <!-- Help & Support Section -->
    <div class="info-section">
      <h4>Help & Support</h4>
      <div class="help-links">
        <a
          href="https://github.com/shaxs/print-vault"
          target="_blank"
          rel="noopener noreferrer"
          class="help-link"
        >
          <span class="icon">📦</span>
          <div>
            <strong>GitHub Repository</strong>
            <p>View source code and contribute</p>
          </div>
        </a>

        <a
          href="https://github.com/shaxs/print-vault/blob/main/README.md"
          target="_blank"
          rel="noopener noreferrer"
          class="help-link"
        >
          <span class="icon">📖</span>
          <div>
            <strong>Documentation</strong>
            <p>Learn how to use Print Vault</p>
          </div>
        </a>

        <a
          href="https://github.com/shaxs/print-vault/issues"
          target="_blank"
          rel="noopener noreferrer"
          class="help-link"
        >
          <span class="icon">🐛</span>
          <div>
            <strong>Bugs or Issues</strong>
            <p>Have you found a bug or need to report an issue? Open a ticket on Github</p>
          </div>
        </a>

        <a
          href="https://discord.com/channels/460117602945990666/1432161560578756618"
          target="_blank"
          rel="noopener noreferrer"
          class="help-link"
        >
          <div class="discord-icon">
            <svg
              xmlns="http://www.w3.org/2000/svg"
              viewBox="0 0 127.14 96.36"
              width="28"
              height="28"
            >
              <path
                fill="#5865F2"
                d="M107.7,8.07A105.15,105.15,0,0,0,81.47,0a72.06,72.06,0,0,0-3.36,6.83A97.68,97.68,0,0,0,49,6.83,72.37,72.37,0,0,0,45.64,0,105.89,105.89,0,0,0,19.39,8.09C2.79,32.65-1.71,56.6.54,80.21h0A105.73,105.73,0,0,0,32.71,96.36,77.7,77.7,0,0,0,39.6,85.25a68.42,68.42,0,0,1-10.85-5.18c.91-.66,1.8-1.34,2.66-2a75.57,75.57,0,0,0,64.32,0c.87.71,1.76,1.39,2.66,2a68.68,68.68,0,0,1-10.87,5.19,77,77,0,0,0,6.89,11.1A105.25,105.25,0,0,0,126.6,80.22h0C129.24,52.84,122.09,29.11,107.7,8.07ZM42.45,65.69C36.18,65.69,31,60,31,53s5-12.74,11.43-12.74S54,46,53.89,53,48.84,65.69,42.45,65.69Zm42.24,0C78.41,65.69,73.25,60,73.25,53s5-12.74,11.44-12.74S96.23,46,96.12,53,91.08,65.69,84.69,65.69Z"
              />
            </svg>
          </div>
          <div>
            <strong>Discord</strong>
            <p>Chat with us and get support in the Print Vault channel on the Voron Discord</p>
          </div>
        </a>

        <a href="mailto:printvault@shaxs.net" class="help-link">
          <span class="icon">📧</span>
          <div>
            <strong>Email</strong>
            <p>
              Want to email us directly? You can do so by emailing printvault@shaxs.net. You will
              get faster replies using either Github or Discord however.
            </p>
          </div>
        </a>
      </div>

      <!-- Troubleshooting Tip -->
      <div class="troubleshooting-tip">
        <span class="icon">🔧</span>
        <div>
          <strong>Need to share debug information?</strong>
          <p>
            Use the <strong>Copy Version Info</strong> button above to copy system details. For
            backend errors or stack traces, run:
          </p>
          <code>docker compose logs backend --tail=100</code>
        </div>
      </div>
    </div>

    <!-- License Section -->
    <div class="info-section">
      <h4>License</h4>
      <p>
        Print Vault is licensed under the
        <a
          href="https://github.com/shaxs/print-vault/blob/main/LICENSE"
          target="_blank"
          rel="noopener noreferrer"
          class="license-link"
          >GNU Affero General Public License v3.0 (AGPL-3.0)</a
        >.
      </p>

      <div class="license-details">
        <h5>What this means:</h5>
        <ul>
          <li>
            <span class="check">✅</span> <strong>Free for self-hosting</strong> - Personal and
            commercial use
          </li>
          <li>
            <span class="check">✅</span> <strong>Modify and share</strong> - You can fork and
            improve
          </li>
          <li>
            <span class="warning">⚠️</span> <strong>SaaS restrictions</strong> - If you host Print
            Vault as a service for others, you must open source your modifications
          </li>
        </ul>
        <p class="commercial-note">
          For commercial licensing inquiries, please
          <a
            href="https://github.com/shaxs/print-vault/issues"
            target="_blank"
            rel="noopener noreferrer"
            class="license-link"
            >open an issue</a
          >.
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import APIService from '@/services/APIService'
import packageJson from '../../package.json'

const versionInfo = ref({})
const loading = ref(true)
const error = ref(null)
const copied = ref(false)
const frontendVersion = ref(packageJson.version)
const updateInfo = ref({
  update_available: false,
  latest_version: null,
  current_version: null,
  release_url: null,
  status: 'unknown',
})
const updateDismissed = ref(false)

// Check if frontend and backend versions match
const versionMismatch = computed(() => {
  if (!versionInfo.value.version) return false
  return frontendVersion.value !== versionInfo.value.version
})

// Check localStorage for dismissed updates
const checkDismissedUpdate = () => {
  const dismissed = localStorage.getItem('update_dismissed')
  if (dismissed) {
    const dismissedVersion = localStorage.getItem('dismissed_version')
    // If user dismissed this specific version, keep it dismissed
    if (dismissedVersion === updateInfo.value.latest_version) {
      updateDismissed.value = true
    } else {
      // New version available, clear old dismissal
      localStorage.removeItem('update_dismissed')
      localStorage.removeItem('dismissed_version')
      updateDismissed.value = false
    }
  }
}

const dismissUpdate = () => {
  updateDismissed.value = true
  localStorage.setItem('update_dismissed', 'true')
  localStorage.setItem('dismissed_version', updateInfo.value.latest_version)
}

const fetchVersion = async () => {
  loading.value = true
  error.value = null

  try {
    const response = await APIService.getVersion()
    versionInfo.value = response.data
  } catch (err) {
    console.error('Failed to fetch version info:', err)
    error.value = err.message || 'Unknown error occurred'
  } finally {
    loading.value = false
  }
}

const checkForUpdates = async () => {
  try {
    const response = await APIService.checkForUpdates()
    updateInfo.value = response.data

    // Check if user already dismissed this version
    if (updateInfo.value.update_available) {
      checkDismissedUpdate()
    }
  } catch (err) {
    console.error('Failed to check for updates:', err)
    // Silently fail - update checks are non-critical and shouldn't disrupt user experience
    // (GitHub API may be down, rate-limited, or blocked - version info still loads normally)
  }
}

const formatDateTime = (isoString) => {
  if (!isoString) return 'Unknown'
  try {
    const date = new Date(isoString)
    return date.toLocaleString()
  } catch {
    return isoString
  }
}

const getBrowserInfo = () => {
  const ua = navigator.userAgent
  let browserName = 'Unknown'
  let browserVersion = 'Unknown'
  let os = 'Unknown'

  // Detect browser
  if (ua.indexOf('Firefox') > -1) {
    browserName = 'Firefox'
    browserVersion = ua.match(/Firefox\/([0-9.]+)/)?.[1] || 'Unknown'
  } else if (ua.indexOf('Edg') > -1) {
    browserName = 'Edge'
    browserVersion = ua.match(/Edg\/([0-9.]+)/)?.[1] || 'Unknown'
  } else if (ua.indexOf('Chrome') > -1) {
    browserName = 'Chrome'
    browserVersion = ua.match(/Chrome\/([0-9.]+)/)?.[1] || 'Unknown'
  } else if (ua.indexOf('Safari') > -1) {
    browserName = 'Safari'
    browserVersion = ua.match(/Version\/([0-9.]+)/)?.[1] || 'Unknown'
  }

  // Detect OS
  if (ua.indexOf('Win') > -1) os = 'Windows'
  else if (ua.indexOf('Mac') > -1) os = 'macOS'
  else if (ua.indexOf('Linux') > -1) os = 'Linux'
  else if (ua.indexOf('Android') > -1) os = 'Android'
  else if (ua.indexOf('iPhone') > -1 || ua.indexOf('iPad') > -1) os = 'iOS'

  return { browserName, browserVersion, os }
}

const copyVersionInfo = () => {
  const mismatchNote = versionMismatch.value ? '\n⚠️ VERSION MISMATCH DETECTED' : ''
  const browserInfo = getBrowserInfo()

  // Build migration info string
  let migrationInfo = ''
  if (versionInfo.value.migrations) {
    const mig = versionInfo.value.migrations
    migrationInfo = `\n\nMigration Status:
Applied: ${mig.applied_count} migrations
Unapplied: ${mig.unapplied_count} pending
Latest: ${mig.latest_migration}

All Applied Migrations:
${mig.all_applied ? mig.all_applied.join('\n') : 'None'}`
  }

  const info = `Print Vault Version Information${mismatchNote}

=== Application Versions ===
Frontend Version: ${frontendVersion.value}
Backend Version: ${versionInfo.value.version || 'Unknown'}
Git Commit: ${versionInfo.value.commit || 'unknown'}
Git Branch: ${versionInfo.value.branch || 'unknown'}
Python: ${versionInfo.value.python_version || 'Unknown'}
Django: ${versionInfo.value.django_version || 'Unknown'}
Build Time: ${formatDateTime(versionInfo.value.build_time)}

=== Client Environment ===
Browser: ${browserInfo.browserName} ${browserInfo.browserVersion}
Operating System: ${browserInfo.os}
User Agent: ${navigator.userAgent}${migrationInfo}`

  // Check if Clipboard API is available (requires HTTPS or localhost)
  if (navigator.clipboard && navigator.clipboard.writeText) {
    // Modern Clipboard API (secure contexts only)
    navigator.clipboard
      .writeText(info)
      .then(() => {
        copied.value = true
        setTimeout(() => {
          copied.value = false
        }, 2000)
      })
      .catch((err) => {
        console.error('Failed to copy with Clipboard API:', err)
        // Fallback to legacy method
        fallbackCopy(info)
      })
  } else {
    // Fallback for insecure contexts (HTTP)
    fallbackCopy(info)
  }
}

const fallbackCopy = (text) => {
  // Legacy copy method using textarea and execCommand
  // Works in insecure contexts (HTTP) where Clipboard API is unavailable
  const textarea = document.createElement('textarea')
  textarea.value = text
  textarea.style.position = 'fixed'
  textarea.style.opacity = '0'
  document.body.appendChild(textarea)
  textarea.select()

  try {
    const successful = document.execCommand('copy')
    if (successful) {
      copied.value = true
      setTimeout(() => {
        copied.value = false
      }, 2000)
    } else {
      console.error('Failed to copy using fallback method')
      alert('Failed to copy to clipboard. Please copy manually.')
    }
  } catch (err) {
    console.error('Fallback copy failed:', err)
    alert('Copy to clipboard is not supported in this browser/context.')
  } finally {
    document.body.removeChild(textarea)
  }
}

onMounted(() => {
  // Set initial dismissal state immediately to prevent flash (will be revalidated after API call)
  const dismissed = localStorage.getItem('update_dismissed')
  if (dismissed) {
    updateDismissed.value = true
  }

  fetchVersion()
  checkForUpdates()
})
</script>

<style scoped>
.about-tab-container {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.content-header h3 {
  color: var(--color-heading);
  margin-bottom: 1.5rem;
}

.info-section {
  background-color: var(--color-background);
  border: 1px solid var(--color-border);
  border-radius: 8px;
  padding: 20px;
}

.info-section h4 {
  color: var(--color-heading);
  margin-bottom: 1rem;
  font-size: 1.1rem;
}

.loading,
.error {
  padding: 20px;
  text-align: center;
}

.error {
  color: var(--color-red);
}

.retry-button {
  margin-top: 10px;
  padding: 8px 16px;
  background-color: var(--color-blue);
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.retry-button:hover {
  background-color: #0b5ed7;
}

/* Update Notification Alert - matches Dashboard alert-info style */
.update-notification {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 1rem;
  border-radius: 6px;
  margin-bottom: 1.5rem;
  gap: 1rem;
}

.update-notification.alert-info {
  background: color-mix(in srgb, var(--color-alert-info), transparent 90%);
  border-left: 3px solid var(--color-alert-info);
}

.update-notification .alert-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  min-width: 0;
}

.update-notification .alert-title {
  font-weight: 600;
  color: var(--color-text);
  font-size: 0.95rem;
}

.update-notification .alert-message {
  font-size: 0.9rem;
  color: var(--color-text-muted);
  line-height: 1.5;
}

.update-notification .alert-actions {
  margin-top: 8px;
}

.update-notification .update-link {
  color: var(--color-heading);
  text-decoration: none;
  font-weight: 500;
  font-size: 0.9rem;
}

.update-notification .update-link:hover {
  text-decoration: underline;
}

.update-notification .btn-dismiss {
  background: none;
  border: none;
  color: var(--color-text-muted);
  font-size: 1.2rem;
  cursor: pointer;
  padding: 0;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  flex-shrink: 0;
  transition: all 0.2s;
}

.update-notification .btn-dismiss:hover {
  background-color: var(--color-background-soft);
  color: var(--color-text);
}

/* Version Mismatch Warning - matches Dashboard alert-warning style */
.version-mismatch {
  display: flex;
  align-items: flex-start;
  padding: 1rem;
  border-radius: 6px;
  margin-bottom: 1.5rem;
}

.version-mismatch.alert-warning {
  background: color-mix(in srgb, var(--color-alert-warning), transparent 90%);
  border-left: 3px solid var(--color-alert-warning);
}

.version-mismatch .alert-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  min-width: 0;
}

.version-mismatch .alert-title {
  font-weight: 600;
  color: var(--color-text);
  font-size: 0.95rem;
}

.version-mismatch .alert-message {
  font-size: 0.9rem;
  color: var(--color-text-muted);
  line-height: 1.5;
}

.version-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 1rem;
  margin-bottom: 1rem;
}

.version-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background-color: var(--color-background-soft);
  border-radius: 6px;
  border: 1px solid var(--color-border);
}

.version-item .label {
  font-weight: 500;
  color: var(--color-text-muted);
}

.version-item .value {
  font-weight: 600;
  color: var(--color-text);
}

.version-item .value.monospace {
  font-family: 'Courier New', monospace;
  font-size: 0.9rem;
}

.copy-button {
  width: 100%;
  padding: 10px 16px;
  background-color: var(--color-blue);
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
  transition: background-color 0.2s;
}

.copy-button:hover {
  background-color: var(--color-blue-hover);
}

.help-links {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.help-link {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 15px;
  background-color: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 6px;
  text-decoration: none;
  color: var(--color-text);
  transition: all 0.2s;
}

.help-link:hover {
  background-color: var(--color-background-mute);
  border-color: var(--color-blue);
  transform: translateX(5px);
}

.help-link .icon {
  font-size: 1.5rem;
  flex-shrink: 0;
  min-width: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.help-link .discord-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 28px;
  flex-shrink: 0;
}

.help-link .discord-icon svg {
  display: block;
}

.help-link strong {
  display: block;
  color: var(--color-heading);
  margin-bottom: 4px;
}

.help-link p {
  margin: 0;
  font-size: 0.9rem;
  color: var(--color-text-muted);
}

/* Troubleshooting Tip */
.troubleshooting-tip {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  padding: 16px;
  margin-top: 16px;
  background: var(--color-background-mute);
  border: 1px solid var(--color-border);
  border-radius: 8px;
}

.troubleshooting-tip .icon {
  font-size: 1.5rem;
  flex-shrink: 0;
}

.troubleshooting-tip strong {
  display: block;
  color: var(--color-heading);
  margin-bottom: 8px;
}

.troubleshooting-tip p {
  margin: 0 0 8px 0;
  font-size: 0.9rem;
  color: var(--color-text);
}

.troubleshooting-tip code {
  display: block;
  padding: 8px 12px;
  background: var(--color-background-soft);
  border: 1px solid var(--color-border);
  border-radius: 4px;
  font-family: 'Courier New', monospace;
  font-size: 0.85rem;
  color: var(--color-text);
  user-select: all;
}

.license-link {
  color: var(--color-heading);
  text-decoration: none;
  font-weight: 500;
}

.license-link:hover {
  text-decoration: underline;
}

.license-details {
  margin-top: 1rem;
  padding: 15px;
  background-color: var(--color-background-soft);
  border-radius: 6px;
  border: 1px solid var(--color-border);
}

.license-details h5 {
  color: var(--color-heading);
  margin-bottom: 0.75rem;
  font-size: 1rem;
}

.license-details ul {
  list-style: none;
  padding: 0;
  margin: 0 0 1rem 0;
}

.license-details li {
  padding: 6px 0;
  display: flex;
  align-items: flex-start;
  gap: 8px;
}

.license-details .check {
  color: var(--color-green);
}

.license-details .warning {
  color: var(--color-orange);
}

.commercial-note {
  margin: 0;
  font-size: 0.9rem;
  color: var(--color-text-muted);
}
</style>
