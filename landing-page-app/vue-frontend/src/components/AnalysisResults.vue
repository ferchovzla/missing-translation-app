<template>
  <div class="results-section">
    <div class="results-header">
      <div class="results-info">
        <h3>
          <i class="fas fa-chart-line"></i>
          Analysis Results
        </h3>
        <div class="results-meta">
          <span class="url">{{ result.url }}</span>
          <span class="language">Target: {{ getLanguageName(result.target_language) }}</span>
          <span class="time">{{ result.processing_time.toFixed(2) }}s</span>
        </div>
      </div>
      <button @click="$emit('clear')" class="btn btn-secondary btn-small">
        <i class="fas fa-times"></i>
        Clear Results
      </button>
    </div>

    <!-- Summary Stats -->
    <div class="stats-grid">
      <div class="stat-card">
        <div class="stat-icon" :class="getScoreClass(result.stats.total_issues)">
          <i class="fas fa-exclamation-triangle"></i>
        </div>
        <div class="stat-content">
          <div class="stat-number">{{ result.stats.total_issues }}</div>
          <div class="stat-label">Total Issues</div>
        </div>
      </div>
      
      <div class="stat-card">
        <div class="stat-icon success">
          <i class="fas fa-percentage"></i>
        </div>
        <div class="stat-content">
          <div class="stat-number">{{ result.stats.target_language_percentage.toFixed(1) }}%</div>
          <div class="stat-label">Target Language</div>
        </div>
      </div>
      
      <div class="stat-card">
        <div class="stat-icon info">
          <i class="fas fa-paragraph"></i>
        </div>
        <div class="stat-content">
          <div class="stat-number">{{ result.stats.total_text_blocks }}</div>
          <div class="stat-label">Text Blocks</div>
        </div>
      </div>
    </div>

    <!-- Issues by Severity -->
    <div class="severity-breakdown">
      <h4>Issues by Severity</h4>
      <div class="severity-bars">
        <div
          v-for="(count, severity) in result.stats.issues_by_severity"
          :key="severity"
          class="severity-bar"
        >
          <div class="severity-info">
            <span class="severity-label" :class="severity">
              <i :class="getSeverityIcon(severity)"></i>
              {{ capitalize(severity) }}
            </span>
            <span class="severity-count">{{ count }}</span>
          </div>
          <div class="severity-progress">
            <div
              class="severity-fill"
              :class="severity"
              :style="{ width: `${(count / result.stats.total_issues) * 100}%` }"
            ></div>
          </div>
        </div>
      </div>
    </div>

    <!-- Detected Languages -->
    <div v-if="Object.keys(result.stats.detected_languages).length > 1" class="languages-breakdown">
      <h4>Detected Languages</h4>
      <div class="language-bars">
        <div
          v-for="(percentage, langCode) in result.stats.detected_languages"
          :key="langCode"
          class="language-bar"
        >
          <div class="language-info">
            <span class="language-label">{{ getLanguageName(langCode) }}</span>
            <span class="language-percentage">{{ percentage.toFixed(1) }}%</span>
          </div>
          <div class="language-progress">
            <div
              class="language-fill"
              :style="{ width: `${percentage}%` }"
            ></div>
          </div>
        </div>
      </div>
    </div>

    <!-- Issues List -->
    <div v-if="result.issues.length > 0" class="issues-list">
      <h4>Detailed Issues</h4>
      <div
        v-for="issue in result.issues"
        :key="issue.id"
        class="issue-card"
        :class="issue.severity"
      >
        <div class="issue-header">
          <div class="issue-type">
            <i :class="getIssueIcon(issue.type)"></i>
            <span>{{ formatIssueType(issue.type) }}</span>
          </div>
          <div class="issue-severity" :class="issue.severity">
            <i :class="getSeverityIcon(issue.severity)"></i>
            {{ capitalize(issue.severity) }}
          </div>
        </div>
        
        <div class="issue-content">
          <p class="issue-message">{{ issue.message }}</p>
          <div v-if="issue.snippet" class="issue-snippet">
            <strong>Found text:</strong>
            <code>{{ issue.snippet }}</code>
          </div>
          <div v-if="issue.suggestion" class="issue-suggestion">
            <strong>Suggestion:</strong>
            {{ issue.suggestion }}
          </div>
          <div class="issue-meta">
            <span v-if="issue.confidence" class="confidence">
              Confidence: {{ (issue.confidence * 100).toFixed(0) }}%
            </span>
            <span v-if="issue.xpath" class="xpath" title="XPath location">
              <i class="fas fa-map-marker-alt"></i>
              {{ issue.xpath }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- No Issues -->
    <div v-else class="no-issues">
      <i class="fas fa-check-circle"></i>
      <h3>Great job!</h3>
      <p>No translation quality issues were found in this content.</p>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  result: {
    type: Object,
    required: true
  }
})

defineEmits(['clear'])

const languageMap = {
  es: 'Spanish',
  en: 'English', 
  nl: 'Dutch'
}

const getLanguageName = (code) => {
  return languageMap[code] || code.toUpperCase()
}

const capitalize = (str) => {
  return str.charAt(0).toUpperCase() + str.slice(1)
}

const getScoreClass = (issueCount) => {
  if (issueCount === 0) return 'success'
  if (issueCount <= 2) return 'warning'
  return 'danger'
}

const getSeverityIcon = (severity) => {
  const icons = {
    high: 'fas fa-exclamation-circle',
    medium: 'fas fa-exclamation-triangle', 
    low: 'fas fa-info-circle'
  }
  return icons[severity] || 'fas fa-question-circle'
}

const getIssueIcon = (type) => {
  const icons = {
    language_leakage: 'fas fa-globe',
    grammar_error: 'fas fa-spell-check',
    placeholder_error: 'fas fa-code',
    consistency_error: 'fas fa-balance-scale',
    formatting_error: 'fas fa-align-left'
  }
  return icons[type] || 'fas fa-exclamation-triangle'
}

const formatIssueType = (type) => {
  return type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
}
</script>

