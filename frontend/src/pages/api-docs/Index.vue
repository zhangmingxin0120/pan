<script setup lang="ts">
import { ref } from 'vue'
import { Check, Copy, ExternalLink } from '@vicons/tabler'
import AppIcon from '@/components/base/AppIcon.vue'
import CodeBlock from '@/components/docs/CodeBlock.vue'
import EndpointDoc from '@/components/docs/EndpointDoc.vue'

const copied = ref('')

async function copy(value: string, key: string) {
  await navigator.clipboard.writeText(value)
  copied.value = key
  window.setTimeout(() => {
    if (copied.value === key) copied.value = ''
  }, 1600)
}

const authExample = `curl https://pan.example.com/api/v1/open/findlist \\
  -H "Authorization: Bearer $PAN_API_KEY"`

const findListResponse = `{
  "items": [
    {
      "id": "9d91d70a-...",
      "parent_id": null,
      "kind": "folder",
      "name": "我的文件",
      "is_root": true,
      "size_bytes": 0,
      "content_type": null,
      "created_at": "2026-07-22T10:00:00Z",
      "updated_at": "2026-07-22T10:00:00Z",
      "trashed_at": null
    }
  ],
  "total": 1
}`

const uploadExample = `curl -X POST https://pan.example.com/api/v1/open/upload \\
  -H "Authorization: Bearer $PAN_API_KEY" \\
  -F "parent_id=9d91d70a-..." \\
  -F "file=@./contract.pdf"`

const errorResponse = `{
  "code": "API_PERMISSION_DENIED",
  "message": "API 应用没有 write 权限"
}`

</script>

<template>
  <div class="docs-page">
    <header class="topbar">
      <a class="brand" href="/"><span class="brand-mark">P</span><strong>Pan</strong><span>开发者文档</span></a>
      <div class="top-actions"><span class="version">API v1</span><a href="/admin">管理后台 <AppIcon :icon="ExternalLink" /></a></div>
    </header>

    <div class="docs-layout">
      <aside class="sidebar">
        <nav>
          <strong>开始使用</strong>
          <a href="#overview">开放 API</a>
          <a href="#authentication">身份认证</a>
          <a href="#errors">错误处理</a>
          <strong>资源查询</strong>
          <a href="#findlist"><code>GET</code> findlist</a>
          <a href="#folder-list"><code>GET</code> 目录内容</a>
          <a href="#node-info"><code>GET</code> 资源详情</a>
          <strong>文件管理</strong>
          <a href="#create-folder"><code class="post">POST</code> 新建文件夹</a>
          <a href="#upload"><code class="post">POST</code> 上传文件</a>
          <a href="#rename"><code class="patch">PATCH</code> 重命名</a>
          <a href="#move"><code class="post">POST</code> 移动</a>
          <a href="#download"><code>GET</code> 下载</a>
          <a href="#delete"><code class="delete">DELETE</code> 删除</a>
        </nav>
      </aside>

      <main class="docs-content">
        <section id="overview" class="hero">
          <span class="eyebrow">PAN OPEN API</span>
          <h1>把 Pan 作为你的文件服务</h1>
          <p>通过一个独立 API Key，让外部产品安全地管理绑定账号下的全部文件和文件夹。接口沿用账号容量、文件大小和回收站规则。</p>
          <div class="base-url"><span>Base URL</span><code>https://你的域名/api/v1/open</code><button @click="copy('/api/v1/open', 'base')"><AppIcon :icon="copied === 'base' ? Check : Copy" /></button></div>
          <div class="principles">
            <article><strong>账号隔离</strong><span>每个 API 应用只能访问绑定账号，不能跨账号读取资源。</span></article>
            <article><strong>独立权限</strong><span>读取、写入和删除权限分别控制，密钥可随时停用或轮换。</span></article>
            <article><strong>统一规则</strong><span>外部上传同样计入账号配额，删除操作统一进入回收站。</span></article>
          </div>
        </section>

        <section id="authentication" class="doc-section">
          <div class="section-title"><span>01</span><div><h2>身份认证</h2><p>所有请求通过 HTTP Bearer API Key 认证。</p></div></div>
          <div class="callout warning"><strong>妥善保存 API Key</strong><span>完整密钥只在创建或轮换时显示一次。不要写入前端代码、公开仓库或浏览器页面。</span></div>
          <CodeBlock title="请求示例" :code="authExample" copy-key="auth" :copied="copied" @copy="copy" />
        </section>

        <section id="findlist" class="doc-section endpoint-section">
          <div class="endpoint-heading"><span class="method get">GET</span><code>/findlist</code></div>
          <h2>查询账号资源</h2>
          <p>这是外部对接最常用的查询接口。不传参数时返回绑定账号下全部有效文件和文件夹；传入参数后可查询具体资源、目录内容或名称搜索。</p>
          <h3>Query 参数</h3>
          <div class="param-table">
            <div class="table-head"><span>参数</span><span>类型</span><span>必填</span><span>说明</span></div>
            <div><code>node_id</code><span>UUID</span><span>否</span><span>查询一个具体文件或文件夹</span></div>
            <div><code>parent_id</code><span>UUID</span><span>否</span><span>只返回该文件夹的直接子内容</span></div>
            <div><code>keyword</code><span>string</span><span>否</span><span>在整个绑定账号中按名称模糊搜索</span></div>
          </div>
          <div class="callout"><strong>组合规则</strong><span><code>keyword</code> 可以与 <code>parent_id</code> 组合；<code>node_id</code> 和 <code>parent_id</code> 不能同时使用。</span></div>
          <div class="examples-grid">
            <div><h3>全部资源</h3><code>GET /findlist</code></div>
            <div><h3>指定资源</h3><code>GET /findlist?node_id=UUID</code></div>
            <div><h3>目录内容</h3><code>GET /findlist?parent_id=UUID</code></div>
            <div><h3>搜索名称</h3><code>GET /findlist?keyword=合同</code></div>
          </div>
          <CodeBlock title="200 Response" :code="findListResponse" copy-key="find-response" :copied="copied" @copy="copy" />
        </section>

        <EndpointDoc id="folder-list" method="GET" path="/nodes" title="分页浏览目录" description="分页获取根目录或指定文件夹的直接内容，同时返回面包屑。适合制作文件管理界面。" params="Query: parent_id、search、page、page_size" response="200 · items、total、page、page_size、breadcrumbs、current_folder" />
        <EndpointDoc id="node-info" method="GET" path="/nodes/{node_id}" title="获取资源详情" description="根据 UUID 返回一个文件或文件夹的元数据。需要读取权限。" params="Path: node_id" response="200 · Node 对象" />
        <EndpointDoc id="create-folder" method="POST" path="/folders" title="新建文件夹" description="在根目录或指定父目录中新建文件夹。需要写入权限。" params="JSON: name、parent_id（可选）" response="201 · 新建文件夹的 Node 对象" />

        <section id="upload" class="doc-section endpoint-section">
          <div class="endpoint-heading"><span class="method post">POST</span><code>/upload</code></div>
          <h2>上传文件</h2>
          <p>使用 <code>multipart/form-data</code> 上传一个文件。未传 <code>parent_id</code> 时上传到账号根目录。</p>
          <div class="param-table compact">
            <div class="table-head"><span>字段</span><span>类型</span><span>必填</span><span>说明</span></div>
            <div><code>file</code><span>binary</span><span>是</span><span>待上传文件</span></div>
            <div><code>parent_id</code><span>UUID</span><span>否</span><span>目标文件夹</span></div>
          </div>
          <div class="inline-param"><strong>成功返回</strong><code>201 · 已上传文件的 Node 对象</code></div>
          <CodeBlock title="cURL" :code="uploadExample" copy-key="upload" :copied="copied" @copy="copy" />
        </section>

        <EndpointDoc id="rename" method="PATCH" path="/nodes/{node_id}/name" title="重命名" description="修改文件或文件夹名称。同级不能存在同名内容。需要写入权限。" params="Path: node_id；JSON: name" response="200 · 更新后的 Node 对象" />
        <EndpointDoc id="move" method="POST" path="/nodes/{node_id}/move" title="移动资源" description="将文件或文件夹移动到另一个目录。需要写入权限。" params="Path: node_id；JSON: target_parent_id" response="200 · 更新后的 Node 对象" />
        <EndpointDoc id="download" method="GET" path="/nodes/{node_id}/download" title="下载文件" description="返回原始文件流，并记录到该 API 应用的下载流量。需要读取权限。" params="Path: node_id" response="200 · 原始文件二进制流，包含 Content-Disposition" />
        <EndpointDoc id="delete" method="DELETE" path="/nodes/{node_id}" title="删除资源" description="将文件或文件夹移入绑定账号的回收站，不执行永久删除。需要删除权限。" params="Path: node_id" response="204 · 无响应体" />

        <section id="errors" class="doc-section">
          <div class="section-title"><span>02</span><div><h2>错误处理</h2><p>所有业务错误使用一致的 JSON 结构。</p></div></div>
          <CodeBlock title="Error Response" :code="errorResponse" copy-key="error" :copied="copied" @copy="copy" />
          <div class="status-list">
            <div><code>401</code><span>API Key 缺失、格式错误或已经轮换失效</span></div>
            <div><code>403</code><span>API 应用被停用、账号被停用或缺少操作权限</span></div>
            <div><code>404</code><span>资源不存在，或者不属于 API 绑定账号</span></div>
            <div><code>409</code><span>同一目录存在同名文件或文件夹</span></div>
            <div><code>413</code><span>超出账号容量或单文件大小限制</span></div>
            <div><code>422</code><span>请求参数、名称或移动目标不合法</span></div>
          </div>
        </section>

        <footer>Pan Open API · Version 1</footer>
      </main>
    </div>
  </div>
</template>

<style lang="scss">
@use '@/assets/styles/variables' as *;
.docs-page { min-height: 100vh; color: #182230; background: #fff;
.topbar { position: sticky; top: 0; z-index: 20; height: 64px; display: flex; align-items: center; justify-content: space-between; padding: 0 32px; border-bottom: 1px solid #e7ebf0; background: rgb(255 255 255 / 94%); backdrop-filter: blur(12px); }.brand { display: flex; align-items: center; gap: 9px; color: inherit; text-decoration: none; }.brand-mark { width: 30px; height: 30px; display: grid; place-items: center; border-radius: 9px; color: #fff; background: $primary; font-weight: 700; }.brand > span:last-child { padding-left: 9px; border-left: 1px solid #dfe4ea; color: #687386; font-size: 13px; }.top-actions { display: flex; align-items: center; gap: 20px; }.top-actions a { display: flex; align-items: center; gap: 5px; color: #536174; font-size: 13px; text-decoration: none; }.version { padding: 5px 9px; border-radius: 999px; color: #176b52; background: #e8f7f1; font-size: 11px; font-weight: 650; }
.docs-layout { display: grid; grid-template-columns: 252px minmax(0, 1fr); }.sidebar { position: sticky; top: 64px; height: calc(100vh - 64px); overflow: auto; padding: 28px 22px; border-right: 1px solid #edf0f3; background: #fbfcfd; }.sidebar nav { display: grid; gap: 3px; }.sidebar strong { margin: 18px 10px 6px; color: #8a94a3; font-size: 10px; letter-spacing: .1em; text-transform: uppercase; }.sidebar strong:first-child { margin-top: 0; }.sidebar a { display: flex; align-items: center; gap: 8px; padding: 7px 10px; border-radius: 7px; color: #4b596c; font-size: 13px; text-decoration: none; }.sidebar a:hover { color: $primary; background: #eef6ff; }.sidebar code { width: 38px; color: #16765a; font-size: 9px; font-weight: 700; }.sidebar code.post { color: #8a55d6; }.sidebar code.patch { color: #b56a16; }.sidebar code.delete { color: #cb3b4c; }
.docs-content { width: min(900px, calc(100% - 72px)); margin: 0 auto; padding: 64px 0 80px; }.hero { padding-bottom: 56px; border-bottom: 1px solid #e8ecf0; }.eyebrow { color: $primary; font-size: 11px; font-weight: 700; letter-spacing: .16em; }.hero h1 { max-width: 650px; margin: 12px 0 16px; font-size: clamp(34px, 5vw, 52px); line-height: 1.08; letter-spacing: -.035em; }.hero > p { max-width: 700px; margin: 0; color: #607086; font-size: 17px; line-height: 1.75; }.base-url { display: flex; align-items: center; gap: 12px; margin-top: 28px; padding: 13px 16px; border: 1px solid #dce4eb; border-radius: 10px; background: #f8fafc; }.base-url span { color: #7b8797; font-size: 11px; font-weight: 650; text-transform: uppercase; }.base-url code { flex: 1; color: #26364a; }.base-url button, .code-head button { display: flex; align-items: center; gap: 5px; border: 0; color: #647286; background: transparent; cursor: pointer; }.principles { display: grid; grid-template-columns: repeat(3, 1fr); gap: 14px; margin-top: 24px; }.principles article { display: grid; gap: 6px; padding: 17px; border: 1px solid #e5e9ee; border-radius: 10px; }.principles article span { color: #6d798a; font-size: 12px; line-height: 1.6; }
.doc-section { padding: 56px 0; border-bottom: 1px solid #e8ecf0; scroll-margin-top: 78px; }.section-title { display: flex; gap: 15px; align-items: flex-start; }.section-title > span { width: 30px; height: 30px; display: grid; place-items: center; border-radius: 50%; color: $primary; background: #edf6ff; font-size: 11px; font-weight: 700; }.section-title h2, .endpoint-section h2 { margin: 0; font-size: 26px; letter-spacing: -.02em; }.section-title p, .endpoint-section > p { margin: 8px 0 0; color: #667487; line-height: 1.7; }.doc-section h3 { margin: 28px 0 10px; font-size: 14px; }.endpoint-heading { display: flex; align-items: center; gap: 12px; margin-bottom: 18px; }.endpoint-heading > code { color: #253449; font-size: 14px; }.method { padding: 5px 8px; border-radius: 5px; color: #147458; background: #e8f7f1; font-size: 10px; font-weight: 800; }.method.post { color: #7651b5; background: #f2ecfb; }.method.patch { color: #a35e0c; background: #fff2df; }.method.delete { color: #bc3545; background: #ffebee; }
.callout { display: grid; gap: 4px; margin: 20px 0; padding: 14px 16px; border-left: 3px solid $primary; border-radius: 0 8px 8px 0; background: #f1f7fd; }.callout strong { font-size: 13px; }.callout span { color: #607086; font-size: 12px; line-height: 1.6; }.callout.warning { border-color: #e3a23b; background: #fff8e9; }.code-block { overflow: hidden; margin-top: 18px; border: 1px solid #dbe2e9; border-radius: 10px; background: #111a27; }.code-head { display: flex; align-items: center; justify-content: space-between; padding: 9px 13px; border-bottom: 1px solid #293445; color: #8f9cad; font-size: 11px; }.code-head button { color: #aeb8c5; font-size: 11px; }.code-block pre { overflow: auto; margin: 0; padding: 18px; color: #d8e2ed; font-size: 12px; line-height: 1.65; }.param-table { margin-top: 10px; border: 1px solid #e1e6eb; border-radius: 9px; }.param-table > div { display: grid; grid-template-columns: 1fr .7fr .5fr 2.2fr; gap: 12px; padding: 11px 14px; border-top: 1px solid #edf0f3; color: #586678; font-size: 12px; }.param-table > div:first-child { border: 0; }.param-table .table-head { color: #8a94a3; background: #fafbfc; font-size: 10px; font-weight: 650; text-transform: uppercase; }.param-table code { color: #245d93; }.examples-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; margin: 20px 0; }.examples-grid > div { padding: 13px 15px; border: 1px solid #e4e9ee; border-radius: 8px; }.examples-grid h3 { margin: 0 0 6px; color: #7b8796; font-size: 10px; }.examples-grid code { color: #27445f; font-size: 11px; }.inline-param { display: flex; gap: 12px; margin-top: 18px; padding: 12px 14px; border-radius: 8px; background: #f6f8fa; font-size: 12px; }.inline-param code { color: #315b82; }.status-list { display: grid; margin-top: 20px; }.status-list > div { display: grid; grid-template-columns: 58px 1fr; padding: 11px 0; border-bottom: 1px solid #edf0f2; color: #647184; font-size: 12px; }.status-list code { color: #b23b48; font-weight: 700; }.docs-content footer { padding-top: 40px; color: #99a2ae; font-size: 11px; }
@media (max-width: 800px) { .topbar { padding: 0 18px; }.top-actions a { display: none; }.docs-layout { display: block; }.sidebar { display: none; }.docs-content { width: min(100% - 36px, 700px); padding-top: 42px; }.principles { grid-template-columns: 1fr; }.param-table > div { grid-template-columns: 1fr .6fr .45fr 1.7fr; }.examples-grid { grid-template-columns: 1fr; } }
@media (max-width: 520px) { .brand > span:last-child { display: none; }.hero h1 { font-size: 34px; }.base-url { align-items: flex-start; flex-direction: column; }.base-url code { word-break: break-all; }.param-table { overflow-x: auto; }.param-table > div { min-width: 620px; }.docs-content { width: calc(100% - 28px); } }
}
</style>
