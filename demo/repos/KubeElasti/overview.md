KubeElasti is a Kubernetes-native autoscaling solution designed to dynamically manage and scale services based on real-time traffic and resource utilization. It comprises a `Resolver` module that acts as a reverse proxy, observing incoming requests and applying traffic management policies, and an `Operator` module that orchestrates the scaling of `ElastiService` custom resources within the Kubernetes cluster. A shared `Pkg` module provides common utilities and foundational services to both core components, ensuring efficient and responsive resource management.

```mermaid
graph TD
    subgraph KubeElasti System
        operator[Operator Module]
        resolver[Resolver Module]
        pkg[Pkg Module]
    end

    resolver -- Observes Traffic & Triggers Scaling --> operator
    operator -- Manages ElastiService CRs & Scales Resources --> resolver
    operator -- Utilizes Common Services --> pkg
    resolver -- Utilizes Common Services --> pkg

    click operator "operator.md" "View Operator Module Documentation"
    click resolver "resolver.md" "View Resolver Module Documentation"
    click pkg "pkg.md" "View Pkg Module Documentation"
```