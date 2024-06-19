# 项目名称

关于 JFrog 产品的一些工具

## 目录

- [简介](#简介)
- [Artifactory Repo Index](#artifactory-repo-index)

## 简介

关于 JFrog 产品，如 Artifactoroy 、 Xray 的一些小工具，帮助用户更好的使用、维护 JFrog 平台。


## Artifactory Repo Index
该项目是一个Python脚本，用于对JFrog Xray的 Indexed Resources 的数据进行解释；
主要针对这种场景：
- 点击index all后，进度一直无法达到100%; 
- 似乎某（几）个包index失败，但是由于index数据可能很多，不方便进行日志排查;
- 此脚本可以快速找出这个'异常的'问题；（并不能提供具体的失败原因，只定位包的位置）

[详情点击 Artifactory Repo Index](https://github.com/JFrogChina/MaintainenceTools/tree/main/artifactory-repo-index)
<div style="text-align: center;">
    <img src="https://github.com/JFrogChina/MaintainenceTools/blob/main/artifactory-repo-index/resource/images/indexresource01.jpg?raw=true" alt="图一" />
</div>
## 贡献

欢迎贡献！请 fork 本仓库并提交 PR。
