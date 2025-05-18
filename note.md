# MCP 后端集成说明

本文档面向后端开发使用 Spring Boot + Maven 的同学，描述如何将 Python MCP 服务集成到后端项目中。

## 一、环境准备

1. 安装 Python（>=3.8）并创建虚拟环境：
   ```bash
   cd <项目根目录>
   python -m venv .venv
   source .venv/bin/activate   # Linux / macOS
   .\.venv\Scripts\activate  # Windows PowerShell
   ```
2. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```
3. 在根目录下添加 `.env` 文件，设置以下环境变量：
   ```text
   NCBI_EMAIL=your_email@example.com
   NCBI_API_KEY=<可选：NCBI API Key>
   SILICONFLOW_API_KEY=<SiliconFlow API Key>
   ```

## 二、启动 MCP 服务

1. 在项目根目录下运行：
   ```bash
   python -m mcp_pubmed_service.main
   ```
2. 默认监听地址：`http://localhost:8000`

## 三、Spring Boot 调用示例

### 1. 添加依赖（`pom.xml`）
```xml
<dependency>
  <groupId>org.springframework.boot</groupId>
  <artifactId>spring-boot-starter-web</artifactId>
</dependency>
```

### 2. 配置 RestTemplate Bean
```java
@Configuration
public class RestConfig {
    @Bean
    public RestTemplate restTemplate() {
        return new RestTemplate();
    }
}
```

### 3. 定义请求参数类
```java
public class SearchRequest {
    private String query;
    private String email;
    private String from_date;
    private String to_date;
    private Integer limit;
    private String order_by;
    private String output;
    // getters/setters
}
public class SummarizeRequest {
    private List<String> filenames;
    private String model;
    private Integer max_tokens;
    private Double temperature;
    // getters/setters
}
public class CitationsRequest {
    private List<String> filenames;
    // getters/setters
}
```

### 4. 编写 Controller 调用 MCP 服务
```java
@RestController
@RequestMapping("/api/pubmed")
public class PubMedController {

    @Autowired
    private RestTemplate restTemplate;

    private static final String MCP_URL = "http://localhost:8000";

    @PostMapping("/search")
    public ResponseEntity<Map> search(@RequestBody SearchRequest req) {
        String url = MCP_URL + "/tool/fetch_articles";
        return restTemplate.postForEntity(url, req, Map.class);
    }

    @PostMapping("/summarize")
    public ResponseEntity<Map> summarize(@RequestBody SummarizeRequest req) {
        String url = MCP_URL + "/tool/summarize_abstracts";
        return restTemplate.postForEntity(url, req, Map.class);
    }

    @PostMapping("/citations")
    public ResponseEntity<Map> citations(@RequestBody CitationsRequest req) {
        String url = MCP_URL + "/tool/format_citations";
        return restTemplate.postForEntity(url, req, Map.class);
    }
}
```

### 5. 错误与状态处理
- 根据返回的 `status` 字段（如 `fetch_completed`、`fetch_failed`、`no_results`、`summary_completed`、`summary_failed`、`format_failed` 等）在后端做相应分支。
- 可统一捕获 HTTP 异常并转化为业务异常。

## 四、部署建议

- 将 Python MCP 服务与 Spring Boot 部署在同一网络或同一集群内。
- 可使用 Docker 容器化运行：
  - 构建 Python 镜像，暴露 8000 端口
  - 在 Spring Boot Docker Compose 中添加该服务
- 使用健康检查（Health Check）和重试机制保障稳定性。


---
*文档结束* 