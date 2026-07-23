<script setup lang="ts">
import { ref } from 'vue'
import { Check, Copy, ExternalLink } from '@vicons/tabler'
import AppIcon from '@/components/base/AppIcon.vue'
import CodeBlock from '@/components/docs/CodeBlock.vue'
import EndpointDoc, { type ApiError, type ApiField } from '@/components/docs/EndpointDoc.vue'

type Endpoint = {
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
}

const copied = ref('')

async function copy(value: string, key: string) {
  await navigator.clipboard.writeText(value)
  copied.value = key
  window.setTimeout(() => {
    if (copied.value === key) copied.value = ''
  }, 1600)
}

const baseUrl = 'https://你的域名/api/v1/open'

const authExample = `curl https://pan.example.com/api/v1/open/findlist \\
  -H "Authorization: Bearer $PAN_API_KEY"`

const aiBrief = `你正在对接 Pan Open API。
Base URL: https://你的域名/api/v1/open
认证方式: 所有接口都在服务端调用，Header 使用 Authorization: Bearer <API_KEY>
权限边界: API Key 只访问后台绑定账号下的资源，不能跨账号访问。
核心模型: Node 表示文件或文件夹。kind=folder/file，is_root=true 表示账号根目录。
常用流程: GET /findlist 获取资源；POST /folders 创建文件夹；POST /upload 上传文件；GET /nodes/{node_id}/download 下载文件。
注意: 删除接口只进入回收站，不做永久删除；上传会占用绑定账号容量。`

const nodeResponse = `{
  "id": "9d91d70a-5a5d-4f4f-a9f4-3ad8f38f0450",
  "parent_id": "3e8c4d19-1f53-44a0-a377-9937f52f1068",
  "kind": "file",
  "name": "contract.pdf",
  "is_root": false,
  "size_bytes": 245760,
  "content_type": "application/pdf",
  "created_at": "2026-07-22T10:00:00Z",
  "updated_at": "2026-07-22T10:00:00Z",
  "trashed_at": null
}`

const errorResponse = `{
  "code": "API_PERMISSION_DENIED",
  "message": "API 应用没有 write 权限"
}`

const commonErrors: ApiError[] = [
  { status: '401', code: 'API_KEY_REQUIRED', description: '缺少 Authorization: Bearer <API_KEY>' },
  { status: '401', code: 'INVALID_API_KEY', description: 'API Key 无效、格式错误或已经轮换失效' },
  { status: '403', code: 'API_APPLICATION_DISABLED', description: 'API 应用已被管理员停用' },
  { status: '403', code: 'ACCOUNT_DISABLED', description: '绑定账号已被管理员停用' },
  { status: '403', code: 'API_PERMISSION_DENIED', description: 'API 应用缺少当前操作所需的 read/write/delete 权限' },
]

const nodeFields: ApiField[] = [
  { name: 'id', type: 'UUID', description: '文件或文件夹的唯一 ID，后续查询、移动、下载都使用它' },
  { name: 'parent_id', type: 'UUID | null', description: '父文件夹 ID。账号根目录为 null' },
  { name: 'kind', type: 'folder | file', description: '资源类型：folder 表示文件夹，file 表示文件' },
  { name: 'name', type: 'string', description: '资源名称' },
  { name: 'is_root', type: 'boolean', description: '是否为账号根目录。根目录不可重命名、移动或删除' },
  { name: 'size_bytes', type: 'number', description: '文件大小，单位 byte。文件夹通常为 0' },
  { name: 'content_type', type: 'string | null', description: '文件 MIME 类型。文件夹为 null' },
  { name: 'created_at', type: 'datetime', description: '创建时间，ISO 8601 格式' },
  { name: 'updated_at', type: 'datetime', description: '最近更新时间，ISO 8601 格式' },
  { name: 'trashed_at', type: 'datetime | null', description: '进入回收站时间。开放接口默认只返回未删除资源' },
]

const endpoints: Endpoint[] = [
  {
    id: 'findlist',
    method: 'GET',
    path: '/findlist',
    englishName: 'findList',
    title: '查询账号资源',
    description:
      '这是外部对接最常用的查询接口。不传参数时返回绑定账号下全部有效文件和文件夹；传入参数后可查询具体资源、目录内容或按名称搜索。',
    query: [
      { name: 'node_id', type: 'UUID', example: '9d91d70a-...', description: '查询一个具体文件或文件夹。不能和 parent_id 同时传' },
      { name: 'parent_id', type: 'UUID', example: '3e8c4d19-...', description: '只返回指定文件夹的直接子内容' },
      { name: 'keyword', type: 'string', example: '合同', description: '按名称模糊搜索。可以和 parent_id 组合使用' },
    ],
    response: [
      { name: 'items', type: 'Node[]', description: '匹配到的资源列表，文件夹优先，并按 updated_at 倒序排列' },
      { name: 'total', type: 'number', description: '匹配资源总数' },
    ],
    errors: [
      ...commonErrors,
      { status: '404', code: 'NODE_NOT_FOUND', description: 'node_id 对应资源不存在，或不属于绑定账号' },
      { status: '422', code: 'INVALID_QUERY', description: 'node_id 和 parent_id 不能同时使用' },
      { status: '422', code: 'NOT_A_FOLDER', description: 'parent_id 对应资源不是文件夹' },
    ],
    requestExample: `curl "https://pan.example.com/api/v1/open/findlist?keyword=合同" \\
  -H "Authorization: Bearer $PAN_API_KEY"`,
    responseExample: `{
  "items": [
    ${nodeResponse.split('\n').join('\n    ')}
  ],
  "total": 1
}`,
    note: '如果要让外部系统首次同步全量资源，直接调用 GET /findlist；如果要做文件管理界面，优先使用 GET /nodes 分页浏览。',
  },
  {
    id: 'nodes',
    method: 'GET',
    path: '/nodes',
    englishName: 'listNodes',
    title: '分页浏览目录',
    description: '获取账号根目录或指定文件夹下的直接内容，同时返回面包屑，适合制作文件管理界面。',
    query: [
      { name: 'parent_id', type: 'UUID', example: '3e8c4d19-...', description: '目标文件夹 ID。不传时浏览账号根目录' },
      { name: 'search', type: 'string', example: '合同', description: '在当前目录下按名称模糊搜索' },
      { name: 'page', type: 'number', example: '1', description: '页码，默认 1' },
      { name: 'page_size', type: 'number', example: '50', description: '每页数量，默认 50，最大 100' },
    ],
    response: [
      { name: 'items', type: 'Node[]', description: '当前页资源列表' },
      { name: 'total', type: 'number', description: '当前条件下的资源总数' },
      { name: 'page', type: 'number', description: '当前页码' },
      { name: 'page_size', type: 'number', description: '每页数量' },
      { name: 'breadcrumbs', type: '{ id, name }[]', description: '从根目录到当前目录的路径' },
      { name: 'current_folder', type: 'Node', description: '当前目录信息' },
    ],
    errors: [...commonErrors, { status: '422', code: 'NOT_A_FOLDER', description: 'parent_id 对应资源不是文件夹' }],
    requestExample: `curl "https://pan.example.com/api/v1/open/nodes?page=1&page_size=50" \\
  -H "Authorization: Bearer $PAN_API_KEY"`,
  },
  {
    id: 'node-info',
    method: 'GET',
    path: '/nodes/{node_id}',
    englishName: 'getNode',
    title: '获取资源详情',
    description: '根据 UUID 获取一个文件或文件夹的元数据。',
    pathParams: [{ name: 'node_id', type: 'UUID', example: '9d91d70a-...', description: '文件或文件夹 ID' }],
    response: nodeFields,
    errors: [...commonErrors, { status: '404', code: 'NODE_NOT_FOUND', description: '资源不存在，或不属于绑定账号' }],
    requestExample: `curl https://pan.example.com/api/v1/open/nodes/9d91d70a-5a5d-4f4f-a9f4-3ad8f38f0450 \\
  -H "Authorization: Bearer $PAN_API_KEY"`,
    responseExample: nodeResponse,
  },
  {
    id: 'create-folder',
    method: 'POST',
    path: '/folders',
    englishName: 'createFolder',
    title: '新建文件夹',
    description: '在根目录或指定父文件夹下创建新文件夹。',
    body: [
      { name: 'name', type: 'string', required: '是', example: '合同资料', description: '文件夹名称，1-255 个字符，不能包含 /、\\ 或控制字符' },
      { name: 'parent_id', type: 'UUID | null', required: '否', example: '3e8c4d19-...', description: '父文件夹 ID。不传时创建到账号根目录' },
    ],
    response: nodeFields,
    errors: [
      ...commonErrors,
      { status: '409', code: 'NAME_CONFLICT', description: '同一目录下已存在同名内容' },
      { status: '422', code: 'INVALID_NAME', description: '名称为空或包含非法字符' },
      { status: '422', code: 'NOT_A_FOLDER', description: 'parent_id 对应资源不是文件夹' },
    ],
    requestExample: `curl -X POST https://pan.example.com/api/v1/open/folders \\
  -H "Authorization: Bearer $PAN_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{"name":"合同资料","parent_id":null}'`,
    responseExample: nodeResponse.replace('"kind": "file"', '"kind": "folder"').replace('"content_type": "application/pdf"', '"content_type": null'),
  },
  {
    id: 'upload',
    method: 'POST',
    path: '/upload',
    englishName: 'uploadFile',
    title: '上传文件',
    description: '使用 multipart/form-data 上传一个文件。未传 parent_id 时上传到账号根目录。',
    form: [
      { name: 'file', type: 'binary', required: '是', example: './contract.pdf', description: '待上传文件' },
      { name: 'parent_id', type: 'UUID | null', required: '否', example: '3e8c4d19-...', description: '目标文件夹 ID。不传时上传到根目录' },
    ],
    response: nodeFields,
    errors: [
      ...commonErrors,
      { status: '409', code: 'NAME_CONFLICT', description: '目标目录已存在同名内容' },
      { status: '413', code: 'FILE_TOO_LARGE', description: '超过单文件大小限制' },
      { status: '413', code: 'QUOTA_EXCEEDED', description: '绑定账号剩余容量不足' },
      { status: '422', code: 'NOT_A_FOLDER', description: 'parent_id 对应资源不是文件夹' },
    ],
    requestExample: `curl -X POST https://pan.example.com/api/v1/open/upload \\
  -H "Authorization: Bearer $PAN_API_KEY" \\
  -F "parent_id=3e8c4d19-1f53-44a0-a377-9937f52f1068" \\
  -F "file=@./contract.pdf"`,
    responseExample: nodeResponse,
    note: '上传成功后会计入绑定账号容量，也会计入该 API 应用的上传流量统计。',
  },
  {
    id: 'rename',
    method: 'PATCH',
    path: '/nodes/{node_id}/name',
    englishName: 'renameNode',
    title: '重命名资源',
    description: '修改文件或文件夹名称，同级目录不能存在同名内容。',
    pathParams: [{ name: 'node_id', type: 'UUID', example: '9d91d70a-...', description: '文件或文件夹 ID' }],
    body: [{ name: 'name', type: 'string', required: '是', example: '合同-已盖章.pdf', description: '新的资源名称' }],
    response: nodeFields,
    errors: [
      ...commonErrors,
      { status: '409', code: 'NAME_CONFLICT', description: '同一目录下已存在同名内容' },
      { status: '422', code: 'ROOT_IMMUTABLE', description: '账号根目录不能重命名' },
      { status: '422', code: 'INVALID_NAME', description: '名称为空或包含非法字符' },
    ],
    requestExample: `curl -X PATCH https://pan.example.com/api/v1/open/nodes/9d91d70a-5a5d-4f4f-a9f4-3ad8f38f0450/name \\
  -H "Authorization: Bearer $PAN_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{"name":"合同-已盖章.pdf"}'`,
    responseExample: nodeResponse.replace('"name": "contract.pdf"', '"name": "合同-已盖章.pdf"'),
  },
  {
    id: 'move',
    method: 'POST',
    path: '/nodes/{node_id}/move',
    englishName: 'moveNode',
    title: '移动资源',
    description: '将文件或文件夹移动到另一个文件夹下。',
    pathParams: [{ name: 'node_id', type: 'UUID', example: '9d91d70a-...', description: '要移动的文件或文件夹 ID' }],
    body: [{ name: 'target_parent_id', type: 'UUID | null', required: '是', example: '3e8c4d19-...', description: '目标父文件夹 ID。传 null 表示移动到根目录' }],
    response: nodeFields,
    errors: [
      ...commonErrors,
      { status: '409', code: 'NAME_CONFLICT', description: '目标目录已存在同名内容' },
      { status: '422', code: 'ROOT_IMMUTABLE', description: '账号根目录不能移动' },
      { status: '422', code: 'INVALID_MOVE', description: '不能移动到自身或自己的子文件夹中' },
      { status: '422', code: 'NOT_A_FOLDER', description: '目标位置不是文件夹' },
    ],
    requestExample: `curl -X POST https://pan.example.com/api/v1/open/nodes/9d91d70a-5a5d-4f4f-a9f4-3ad8f38f0450/move \\
  -H "Authorization: Bearer $PAN_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{"target_parent_id":"3e8c4d19-1f53-44a0-a377-9937f52f1068"}'`,
    responseExample: nodeResponse,
  },
  {
    id: 'download',
    method: 'GET',
    path: '/nodes/{node_id}/download',
    englishName: 'downloadFile',
    title: '下载文件',
    description: '返回原始文件流。该接口只支持文件，不支持文件夹。',
    pathParams: [{ name: 'node_id', type: 'UUID', example: '9d91d70a-...', description: '文件 ID' }],
    response: [
      { name: 'body', type: 'binary', description: '原始文件内容' },
      { name: 'Content-Type', type: 'header', description: '文件 MIME 类型' },
      { name: 'Content-Disposition', type: 'header', description: '包含下载文件名' },
    ],
    errors: [
      ...commonErrors,
      { status: '404', code: 'FILE_NOT_FOUND', description: '文件内容不存在，或 node_id 不是文件' },
      { status: '404', code: 'NODE_NOT_FOUND', description: '资源不存在，或不属于绑定账号' },
    ],
    requestExample: `curl -L https://pan.example.com/api/v1/open/nodes/9d91d70a-5a5d-4f4f-a9f4-3ad8f38f0450/download \\
  -H "Authorization: Bearer $PAN_API_KEY" \\
  -o contract.pdf`,
    note: '下载成功后会计入该 API 应用的下载流量统计。',
  },
  {
    id: 'delete',
    method: 'DELETE',
    path: '/nodes/{node_id}',
    englishName: 'deleteNode',
    title: '删除资源',
    description: '将文件或文件夹移入绑定账号的回收站，不执行永久删除。',
    pathParams: [{ name: 'node_id', type: 'UUID', example: '9d91d70a-...', description: '要删除的文件或文件夹 ID' }],
    response: [{ name: '无', type: '204 No Content', description: '删除成功时没有响应体' }],
    errors: [
      ...commonErrors,
      { status: '404', code: 'NODE_NOT_FOUND', description: '资源不存在，或不属于绑定账号' },
      { status: '422', code: 'ROOT_IMMUTABLE', description: '账号根目录不能删除' },
    ],
    requestExample: `curl -X DELETE https://pan.example.com/api/v1/open/nodes/9d91d70a-5a5d-4f4f-a9f4-3ad8f38f0450 \\
  -H "Authorization: Bearer $PAN_API_KEY"`,
  },
]
</script>

<template>
  <div class="docs-page">
    <header class="topbar">
      <a class="brand" href="/">
        <span class="brand-mark">P</span>
        <strong>Pan</strong>
        <span>开放接口手册</span>
      </a>
      <div class="top-actions">
        <span class="version">API v1</span>
        <a href="/admin">管理后台 <AppIcon :icon="ExternalLink" /></a>
      </div>
    </header>

    <div class="docs-layout">
      <aside class="sidebar">
        <nav>
          <strong>开始使用</strong>
          <a href="#overview">接口概览</a>
          <a href="#auth">身份认证</a>
          <a href="#models">数据模型</a>
          <a href="#workflow">对接流程</a>
          <a href="#ai-brief">AI 对接摘要</a>
          <strong>接口列表</strong>
          <a v-for="endpoint in endpoints" :key="endpoint.id" :href="`#${endpoint.id}`">
            <code :class="endpoint.method.toLowerCase()">{{ endpoint.method }}</code>
            {{ endpoint.title }}
          </a>
          <strong>错误处理</strong>
          <a href="#errors">通用错误</a>
        </nav>
      </aside>

      <main class="docs-content">
        <section id="overview" class="hero">
          <span class="eyebrow">PAN OPEN API</span>
          <h1>把 Pan 作为你的文件服务</h1>
          <p>外部系统可以通过服务端接口，管理某个绑定账号下的文件和文件夹。API Key 由管理员创建，权限可分别控制读取、写入和删除。</p>
          <div class="base-url">
            <span>Base URL</span>
            <code>{{ baseUrl }}</code>
            <button @click="copy(baseUrl, 'base')"><AppIcon :icon="copied === 'base' ? Check : Copy" /></button>
          </div>
          <div class="summary-table">
            <div class="table-head"><span>接口名称</span><span>请求路径</span><span>描述</span></div>
            <div v-for="endpoint in endpoints" :key="`sum-${endpoint.id}`">
              <a :href="`#${endpoint.id}`">{{ endpoint.title }}</a>
              <code>{{ endpoint.method }} {{ endpoint.path }}</code>
              <span>{{ endpoint.description }}</span>
            </div>
          </div>
        </section>

        <section id="auth" class="doc-section">
          <div class="section-title"><span>01</span><div><h2>身份认证</h2><p>所有开放接口都应在服务器端调用，不要把 API Key 写入前端、小程序、APP 或公开仓库。</p></div></div>
          <div class="param-table auth-table">
            <div class="table-head"><span>Header</span><span>类型</span><span>必填</span><span>示例</span><span>说明</span></div>
            <div><code>Authorization</code><span>string</span><span>是</span><span>Bearer pan_xxx</span><span>接口调用凭证，由管理员在管理后台创建或轮换</span></div>
          </div>
          <CodeBlock title="请求示例" :code="authExample" copy-key="auth" :copied="copied" @copy="copy" />
        </section>

        <section id="models" class="doc-section">
          <div class="section-title"><span>02</span><div><h2>数据模型</h2><p>开放接口主要围绕 Node 对象工作。Node 既可以是文件，也可以是文件夹。</p></div></div>
          <div class="param-table response-table">
            <div class="table-head"><span>字段名</span><span>类型</span><span>说明</span></div>
            <div v-for="field in nodeFields" :key="field.name"><code>{{ field.name }}</code><span>{{ field.type }}</span><span>{{ field.description }}</span></div>
          </div>
          <CodeBlock title="Node 示例" :code="nodeResponse" copy-key="node-model" :copied="copied" @copy="copy" />
        </section>

        <section id="workflow" class="doc-section">
          <div class="section-title"><span>03</span><div><h2>典型对接流程</h2><p>如果另一个系统要把 Pan 当作文件模块使用，通常按下面顺序接入。</p></div></div>
          <div class="steps">
            <div><strong>1. 后台创建 API 应用</strong><span>选择绑定账号，并按业务需要开启 read、write、delete 权限。</span></div>
            <div><strong>2. 查询资源</strong><span>调用 <code>GET /findlist</code> 或 <code>GET /nodes</code> 找到根目录、目标文件夹和文件 ID。</span></div>
            <div><strong>3. 管理文件</strong><span>用 <code>/folders</code> 创建目录，用 <code>/upload</code> 上传文件，用 <code>/download</code> 下载。</span></div>
            <div><strong>4. 记录业务关联</strong><span>外部系统应保存 Pan 返回的 <code>node_id</code>，后续用它查询、下载、移动或删除。</span></div>
          </div>
        </section>

        <section id="ai-brief" class="doc-section">
          <div class="section-title"><span>04</span><div><h2>AI 对接摘要</h2><p>把下面这段和本文档链接一起交给另一个项目的大模型，它就能更快理解对接边界。</p></div></div>
          <CodeBlock title="给 AI 的对接说明" :code="aiBrief" copy-key="ai-brief" :copied="copied" @copy="copy" />
        </section>

        <EndpointDoc
          v-for="endpoint in endpoints"
          :key="endpoint.id"
          v-bind="endpoint"
          :copied="copied"
          @copy="copy"
        />

        <section id="errors" class="doc-section">
          <div class="section-title"><span>05</span><div><h2>通用错误处理</h2><p>业务错误统一返回 JSON。下载文件接口成功时返回二进制流，失败时仍返回 JSON 错误。</p></div></div>
          <CodeBlock title="错误返回示例" :code="errorResponse" copy-key="error" :copied="copied" @copy="copy" />
          <div class="error-table">
            <div class="table-head"><span>HTTP</span><span>错误码</span><span>说明</span></div>
            <div v-for="item in commonErrors" :key="item.code"><code>{{ item.status }}</code><code>{{ item.code }}</code><span>{{ item.description }}</span></div>
            <div><code>404</code><code>NODE_NOT_FOUND</code><span>资源不存在，或不属于当前 API Key 绑定账号</span></div>
            <div><code>409</code><code>NAME_CONFLICT</code><span>同一目录下已存在同名文件或文件夹</span></div>
            <div><code>413</code><code>FILE_TOO_LARGE</code><span>超过单文件大小限制</span></div>
            <div><code>413</code><code>QUOTA_EXCEEDED</code><span>绑定账号容量不足</span></div>
            <div><code>422</code><code>ROOT_IMMUTABLE</code><span>根目录不能重命名、移动或删除</span></div>
          </div>
        </section>

        <footer>Pan Open API · Version 1</footer>
      </main>
    </div>
  </div>
</template>

<style lang="scss">
@use '@/assets/styles/variables' as *;

.docs-page {
  min-height: 100vh;
  color: #1d2735;
  background: #fff;

  .topbar {
    position: sticky;
    top: 0;
    z-index: 20;
    height: 64px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 32px;
    border-bottom: 1px solid #e5e9ef;
    background: rgb(255 255 255 / 94%);
    backdrop-filter: blur(12px);
  }

  .brand {
    display: flex;
    align-items: center;
    gap: 9px;
    color: inherit;
    text-decoration: none;
  }

  .brand-mark {
    width: 30px;
    height: 30px;
    display: grid;
    place-items: center;
    border-radius: 8px;
    color: #fff;
    background: $primary;
    font-weight: 700;
  }

  .brand > span:last-child {
    padding-left: 9px;
    border-left: 1px solid #dfe4ea;
    color: #687386;
    font-size: 13px;
  }

  .top-actions {
    display: flex;
    align-items: center;
    gap: 20px;
  }

  .top-actions a {
    display: flex;
    align-items: center;
    gap: 5px;
    color: #536174;
    font-size: 13px;
    text-decoration: none;
  }

  .version {
    padding: 5px 9px;
    border-radius: 999px;
    color: #176b52;
    background: #e8f7f1;
    font-size: 11px;
    font-weight: 650;
  }

  .docs-layout {
    display: grid;
    grid-template-columns: 268px minmax(0, 1fr);
  }

  .sidebar {
    position: sticky;
    top: 64px;
    height: calc(100vh - 64px);
    overflow: auto;
    padding: 28px 22px;
    border-right: 1px solid #edf0f3;
    background: #fbfcfd;
  }

  .sidebar nav {
    display: grid;
    gap: 3px;
  }

  .sidebar strong {
    margin: 18px 10px 6px;
    color: #8792a2;
    font-size: 10px;
    letter-spacing: .08em;
  }

  .sidebar strong:first-child {
    margin-top: 0;
  }

  .sidebar a {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 7px 10px;
    border-radius: 7px;
    color: #4b596c;
    font-size: 13px;
    text-decoration: none;
  }

  .sidebar a:hover {
    color: $primary;
    background: #eef6ff;
  }

  .sidebar code {
    width: 42px;
    color: #16765a;
    font-size: 9px;
    font-weight: 700;
  }

  .sidebar code.post {
    color: #7651b5;
  }

  .sidebar code.patch {
    color: #a35e0c;
  }

  .sidebar code.delete {
    color: #bc3545;
  }

  .docs-content {
    width: min(980px, calc(100% - 72px));
    margin: 0 auto;
    padding: 56px 0 80px;
  }

  .hero {
    padding-bottom: 52px;
    border-bottom: 1px solid #e8ecf0;
  }

  .eyebrow {
    color: $primary;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: .12em;
  }

  .hero h1 {
    max-width: 720px;
    margin: 12px 0 16px;
    font-size: 44px;
    line-height: 1.12;
  }

  .hero > p {
    max-width: 760px;
    margin: 0;
    color: #607086;
    font-size: 17px;
    line-height: 1.75;
  }

  .base-url {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-top: 28px;
    padding: 13px 16px;
    border: 1px solid #dce4eb;
    border-radius: 8px;
    background: #f8fafc;
  }

  .base-url span {
    color: #7b8797;
    font-size: 11px;
    font-weight: 650;
  }

  .base-url code {
    flex: 1;
    color: #26364a;
  }

  .base-url button,
  .code-head button {
    display: flex;
    align-items: center;
    gap: 5px;
    border: 0;
    color: #647286;
    background: transparent;
    cursor: pointer;
  }

  .doc-section {
    padding: 50px 0;
    border-bottom: 1px solid #e8ecf0;
    scroll-margin-top: 78px;
  }

  .section-title {
    display: flex;
    gap: 15px;
    align-items: flex-start;
    margin-bottom: 22px;
  }

  .section-title > span {
    width: 30px;
    height: 30px;
    display: grid;
    place-items: center;
    border-radius: 50%;
    color: $primary;
    background: #edf6ff;
    font-size: 11px;
    font-weight: 700;
  }

  .section-title h2,
  .endpoint-section h2 {
    margin: 0;
    font-size: 26px;
  }

  .section-title p,
  .endpoint-section > p {
    margin: 8px 0 0;
    color: #667487;
    line-height: 1.7;
  }

  .doc-block {
    margin-top: 24px;
  }

  .doc-block h3,
  .doc-section h3 {
    margin: 0 0 12px;
    font-size: 16px;
  }

  .field-group {
    margin-top: 18px;
  }

  .field-group h4 {
    margin: 0 0 8px;
    color: #59687a;
    font-size: 13px;
  }

  .endpoint-heading {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 18px;
  }

  .endpoint-heading > code {
    color: #253449;
    font-size: 14px;
  }

  .method {
    padding: 5px 8px;
    border-radius: 5px;
    color: #147458;
    background: #e8f7f1;
    font-size: 10px;
    font-weight: 800;
  }

  .method.post {
    color: #7651b5;
    background: #f2ecfb;
  }

  .method.patch {
    color: #a35e0c;
    background: #fff2df;
  }

  .method.delete {
    color: #bc3545;
    background: #ffebee;
  }

  .meta-strip {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
    margin-top: 20px;
  }

  .meta-strip > div {
    padding: 12px 14px;
    border: 1px solid #e3e8ee;
    border-radius: 8px;
    background: #fbfcfe;
  }

  .meta-strip span {
    display: block;
    margin-bottom: 5px;
    color: #7a8797;
    font-size: 11px;
  }

  .meta-strip strong {
    color: #26364a;
    font-size: 13px;
  }

  .summary-table,
  .param-table,
  .error-table {
    overflow: hidden;
    margin-top: 18px;
    border: 1px solid #e1e6eb;
    border-radius: 8px;
  }

  .summary-table > div,
  .param-table > div,
  .error-table > div {
    display: grid;
    gap: 12px;
    padding: 11px 14px;
    border-top: 1px solid #edf0f3;
    color: #586678;
    font-size: 12px;
    line-height: 1.55;
  }

  .summary-table > div:first-child,
  .param-table > div:first-child,
  .error-table > div:first-child {
    border: 0;
  }

  .summary-table > div {
    grid-template-columns: 1.1fr 1.15fr 2.4fr;
  }

  .param-table > div {
    grid-template-columns: 1fr .8fr .55fr 1fr 2.2fr;
  }

  .response-table > div {
    grid-template-columns: 1fr 1fr 2.8fr;
  }

  .error-table > div {
    grid-template-columns: .7fr 1.4fr 2.6fr;
  }

  .table-head {
    color: #7f8b9a;
    background: #fafbfc;
    font-size: 10px;
    font-weight: 700;
  }

  .summary-table a {
    color: $primary;
    text-decoration: none;
    font-weight: 650;
  }

  .summary-table code,
  .param-table code {
    color: #245d93;
  }

  .error-table code {
    color: #b23b48;
    font-weight: 700;
  }

  .callout {
    display: grid;
    gap: 4px;
    margin: 20px 0;
    padding: 14px 16px;
    border-left: 3px solid $primary;
    border-radius: 0 8px 8px 0;
    background: #f1f7fd;
  }

  .callout strong {
    font-size: 13px;
  }

  .callout span {
    color: #607086;
    font-size: 12px;
    line-height: 1.6;
  }

  .steps {
    display: grid;
    gap: 12px;
  }

  .steps > div {
    display: grid;
    gap: 5px;
    padding: 15px 16px;
    border: 1px solid #e4e9ee;
    border-radius: 8px;
  }

  .steps span {
    color: #657487;
    font-size: 13px;
    line-height: 1.6;
  }

  .code-block {
    overflow: hidden;
    margin-top: 18px;
    border: 1px solid #dbe2e9;
    border-radius: 8px;
    background: #111a27;
  }

  .code-head {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 9px 13px;
    border-bottom: 1px solid #293445;
    color: #8f9cad;
    font-size: 11px;
  }

  .code-head button {
    color: #aeb8c5;
    font-size: 11px;
  }

  .code-block pre {
    overflow: auto;
    margin: 0;
    padding: 18px;
    color: #d8e2ed;
    font-size: 12px;
    line-height: 1.65;
  }

  footer {
    padding-top: 40px;
    color: #99a2ae;
    font-size: 11px;
  }

  @media (max-width: 900px) {
    .topbar {
      padding: 0 18px;
    }

    .top-actions a {
      display: none;
    }

    .docs-layout {
      display: block;
    }

    .sidebar {
      display: none;
    }

    .docs-content {
      width: min(100% - 36px, 760px);
      padding-top: 42px;
    }

    .hero h1 {
      font-size: 34px;
    }

    .meta-strip {
      grid-template-columns: 1fr;
    }

    .summary-table,
    .param-table,
    .error-table {
      overflow-x: auto;
    }

    .summary-table > div {
      min-width: 820px;
    }

    .param-table > div {
      min-width: 900px;
    }

    .response-table > div,
    .error-table > div {
      min-width: 720px;
    }
  }

  @media (max-width: 520px) {
    .brand > span:last-child {
      display: none;
    }

    .base-url {
      align-items: flex-start;
      flex-direction: column;
    }

    .base-url code {
      word-break: break-all;
    }

    .docs-content {
      width: calc(100% - 28px);
    }
  }
}
</style>
