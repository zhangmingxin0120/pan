<script setup lang="ts">
withDefaults(
  defineProps<{
    id?: string
    method?: string
    path?: string
    title?: string
    description?: string
    params?: string
    response?: string
  }>(),
  {
    id: '',
    method: 'GET',
    path: '',
    title: '',
    description: '',
    params: '无',
    response: 'Node 对象',
  },
)
</script>

<template>
  <section :id="id" class="doc-section endpoint-section">
    <div class="endpoint-heading">
      <span class="method" :class="method.toLowerCase()">{{ method }}</span>
      <code>{{ path }}</code>
    </div>
    <h2>{{ title }}</h2>
    <p>{{ description }}</p>
    <div class="inline-param"><strong>请求参数</strong><code>{{ params }}</code></div>
    <div class="inline-param"><strong>成功返回</strong><code>{{ response }}</code></div>
  </section>
</template>
