<script setup lang="ts">
import CodeBlock from '@/components/docs/CodeBlock.vue'

export type ApiField = {
  name: string
  type: string
  required?: string
  example?: string
  description: string
}

export type ApiError = {
  status: string
  code: string
  description: string
}

const props = withDefaults(
  defineProps<{
    id: string
    method: string
    path: string
    englishName: string
    title: string
    description: string
    query?: ApiField[]
    pathParams?: ApiField[]
    body?: ApiField[]
    form?: ApiField[]
    response?: ApiField[]
    errors?: ApiError[]
    requestExample?: string
    responseExample?: string
    note?: string
    copied?: string
  }>(),
  {
    query: () => [],
    pathParams: () => [],
    body: () => [],
    form: () => [],
    response: () => [],
    errors: () => [],
    requestExample: '',
    responseExample: '',
    note: '',
    copied: '',
  },
)

const emit = defineEmits<{ copy: [value: string, key: string] }>()

function relayCopy(value: string, key: string) {
  emit('copy', value, key)
}
</script>

<template>
  <section :id="id" class="doc-section endpoint-section">
    <div class="endpoint-heading">
      <span class="method" :class="method.toLowerCase()">{{ method }}</span>
      <code>{{ path }}</code>
    </div>
    <h2>{{ title }}</h2>
    <p>{{ description }}</p>

    <div class="meta-strip">
      <div><span>接口英文名</span><strong>{{ englishName }}</strong></div>
      <div><span>调用方式</span><strong>服务端 HTTP 调用</strong></div>
      <div><span>认证方式</span><strong>Bearer API Key</strong></div>
    </div>

    <div v-if="query.length || pathParams.length || body.length || form.length" class="doc-block">
      <h3>请求参数</h3>
      <div v-if="pathParams.length" class="field-group">
        <h4>路径参数 Path Parameters</h4>
        <div class="param-table">
          <div class="table-head"><span>参数名</span><span>类型</span><span>必填</span><span>示例</span><span>说明</span></div>
          <div v-for="field in pathParams" :key="`path-${field.name}`">
            <code>{{ field.name }}</code><span>{{ field.type }}</span><span>{{ field.required || '是' }}</span><span>{{ field.example || '-' }}</span><span>{{ field.description }}</span>
          </div>
        </div>
      </div>
      <div v-if="query.length" class="field-group">
        <h4>查询参数 Query String Parameters</h4>
        <div class="param-table">
          <div class="table-head"><span>参数名</span><span>类型</span><span>必填</span><span>示例</span><span>说明</span></div>
          <div v-for="field in query" :key="`query-${field.name}`">
            <code>{{ field.name }}</code><span>{{ field.type }}</span><span>{{ field.required || '否' }}</span><span>{{ field.example || '-' }}</span><span>{{ field.description }}</span>
          </div>
        </div>
      </div>
      <div v-if="body.length" class="field-group">
        <h4>请求体 Request Payload</h4>
        <div class="param-table">
          <div class="table-head"><span>参数名</span><span>类型</span><span>必填</span><span>示例</span><span>说明</span></div>
          <div v-for="field in body" :key="`body-${field.name}`">
            <code>{{ field.name }}</code><span>{{ field.type }}</span><span>{{ field.required || '是' }}</span><span>{{ field.example || '-' }}</span><span>{{ field.description }}</span>
          </div>
        </div>
      </div>
      <div v-if="form.length" class="field-group">
        <h4>表单参数 Form Data</h4>
        <div class="param-table">
          <div class="table-head"><span>字段名</span><span>类型</span><span>必填</span><span>示例</span><span>说明</span></div>
          <div v-for="field in form" :key="`form-${field.name}`">
            <code>{{ field.name }}</code><span>{{ field.type }}</span><span>{{ field.required || '是' }}</span><span>{{ field.example || '-' }}</span><span>{{ field.description }}</span>
          </div>
        </div>
      </div>
    </div>

    <div v-if="response.length" class="doc-block">
      <h3>返回参数</h3>
      <div class="param-table response-table">
        <div class="table-head"><span>参数名</span><span>类型</span><span>说明</span></div>
        <div v-for="field in response" :key="`res-${field.name}`">
          <code>{{ field.name }}</code><span>{{ field.type }}</span><span>{{ field.description }}</span>
        </div>
      </div>
    </div>

    <div v-if="note" class="callout"><strong>注意事项</strong><span>{{ note }}</span></div>

    <div v-if="requestExample || responseExample" class="doc-block">
      <h3>代码示例</h3>
      <CodeBlock v-if="requestExample" title="请求示例" :code="requestExample" :copy-key="`${id}-request`" :copied="props.copied" @copy="relayCopy" />
      <CodeBlock v-if="responseExample" title="返回示例" :code="responseExample" :copy-key="`${id}-response`" :copied="props.copied" @copy="relayCopy" />
    </div>

    <div v-if="errors.length" class="doc-block">
      <h3>错误码</h3>
      <div class="error-table">
        <div class="table-head"><span>HTTP</span><span>错误码</span><span>说明</span></div>
        <div v-for="item in errors" :key="`${item.status}-${item.code}`">
          <code>{{ item.status }}</code><code>{{ item.code }}</code><span>{{ item.description }}</span>
        </div>
      </div>
    </div>
  </section>
</template>
