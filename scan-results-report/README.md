# 项目名称：scan_results_report

## 使用范围
仅用于内部排查，暂时不主动提供给客户

## 功能
- **可选功能**：漏洞库更新
- **主要功能**：GUI、JFrog CLI、Catalog、IDEA 四种类型的扫描结果

## 场景
- **场景一：漏洞缺失**
  - **示例**：org.eclipse.jetty:jetty-io:9.4.11.v20180605.jar CVE-2021-28165
- **场景二：漏洞误报**
  - **示例**：jackson-mapper-asl:1.9.2 CVE-2018-14721
- **场景三：数据差异**
  - **示例**：cn.hutool:hutool-all:5.8.16 GUI 和 CLI 扫描结果不一致
- **场景四：数据差异**
  - **示例**：gav://xmlbeans:xbean:2.2.0 IDEA 未报告，其他方式均报告

## 前提条件
- 制品已经存在于 Artifactory 且所在仓库已经设置 index
  - 如果不存在，则进行下载？是否可以自动实现？

## 参数类型
- **位置参数**：artifact 路径、 CVE 及 主观臆断
- **文件**：每行格式一样，用空格分割

## 主要逻辑
### GUI 的扫描结果
1. 调用 `force reindex` 接口重新扫描数据
2. 调用 `artifact scan status` 获取扫描状态
3. 调用 `artifact summary` 获取扫描结果，保存到临时文件 `logs/.tmpresult-gui.json` 中
4. 与 CVE 进行匹配，生成日志
    - 如果存在，第四列则添加为 `true`，不存在则为 `false`
    - 同时打印到控制台，控制台只打印第一、第二、第四列
    - 如果第四列与第三列不一致，则标记为红色

### 日志格式
| Repository Path | CVEs | Aim | Result |
| --- | --- | --- | --- |
| Artifact1 | cve-xx-xx | true | true |
| Artifact2 | cve-xx-xx | false | true |