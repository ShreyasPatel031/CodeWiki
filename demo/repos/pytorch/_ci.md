# _ci Module Documentation

## Overview

The `_ci` module serves as a central hub for Continuous Integration (CI) related tasks within the PyTorch project. It encompasses various functionalities, from running smoke tests and example code to managing Java Native Interface (JNI) interactions and providing a command-line interface (CLI) for specific tasks like VLLM testing. The module aims to ensure code quality, compatibility, and proper integration of different components.

## Architecture

The `_ci` module is composed of several sub-modules, each responsible for a specific aspect of the CI process. The following diagram provides a high-level overview of the module's architecture and component relationships.

```mermaid
graph LR
    subgraph Java JNI [ .ci.docker.java.jni ]
        A(.ci.docker.java.jni._jmethodID)
        B(.ci.docker.java.jni.JNIInvokeInterface)
        C(.ci.docker.java.jni.JavaVMInitArgs)
        D(.ci.docker.java.jni._jfieldID)
        E(.ci.docker.java.jni.JavaVMAttachArgs)
        F(.ci.docker.java.jni.JNINativeMethod)
        G(.ci.docker.java.jni._JavaVM)
        H(.ci.docker.java.jni.JNINativeInterface)
        I(.ci.docker.java.jni._JNIEnv)
        J(.ci.docker.java.jni.JavaVMOption)
    end
    subgraph Lumen CLI [ .ci.lumen_cli ]
        K(.ci.lumen_cli.cli.lib.core.vllm.vllm_test.VllmTestRunner) --> L(.ci.lumen_cli.cli.lib.common.cli_helper.BaseRunner)
        M(.ci.lumen_cli.cli.lib.common.cli_helper.TargetSpec)
        L(.ci.lumen_cli.cli.lib.common.cli_helper.BaseRunner)
        N(.ci.lumen_cli.cli.lib.core.vllm.vllm_test.TestInpuType)
        O(.ci.lumen_cli.cli.lib.common.cli_helper.RichHelp)
    end
    subgraph PyTorch Examples [ .ci.pytorch ]
        P(.ci.pytorch.test_example_code.cnn_smoke.SimpleCNN)
        Q(.ci.pytorch.test_example_code.cnn_smoke_win_arm64.SimpleCNN)
        R(.ci.pytorch.smoke_test.smoke_test.Net)
    end


    style Java JNI fill:#f9f,stroke:#333,stroke-width:2px
    style Lumen CLI fill:#ccf,stroke:#333,stroke-width:2px
    style PyTorch Examples fill:#ffc,stroke:#333,stroke-width:2px

    linkStyle 0,1,2,3,4,5,6,7,8,9 stroke:#f9f,stroke-width:1px;
    linkStyle 10,11,12,13 stroke:#ccf,stroke-width:1px;
    linkStyle 14,15 stroke:#ffc,stroke-width:1px;

    
```

## Sub-modules and Functionality

1.  **Java JNI:**
    -   Provides definitions and structures for interacting with the Java Native Interface (JNI). This sub-module enables PyTorch components to interface with Java code.
    -   Key components include `_jmethodID`, `JNIInvokeInterface`, `JavaVMInitArgs`, `_jfieldID`, `JavaVMAttachArgs`, `JNINativeMethod`, `_JavaVM`, `JNINativeInterface`, `_JNIEnv`, and `JavaVMOption`.
    -   See more details in [docker.java.jni.md](docker.java.jni.md).


2.  **Lumen CLI:**
    -   Offers a command-line interface (CLI) for specific tasks, particularly related to VLLM testing.
    -   Includes components like `VllmTestRunner` (responsible for running VLLM tests), `TargetSpec` (defines CLI subcommand specifications), `BaseRunner` (an abstract base class for runners), `TestInpuType` (an enumeration of test input types), and `RichHelp` (for enhanced help messages).
    -   See more details in [lumen_cli.md](lumen_cli.md).


3.  **PyTorch Examples:**
    -   Contains example code and smoke tests for PyTorch, including simple CNN models.
    -   Features components such as `SimpleCNN` (a basic CNN model used in smoke tests) and `Net` (another CNN model for testing purposes).
    -   These tests are for verifying core functionalities of PyTorch.


## Integration with PyTorch

The `_ci` module plays a crucial role in the PyTorch CI pipeline. It ensures that the core functionalities of PyTorch are working as expected, and that the integration with other components, such as Java-based systems, is seamless. The module also provides a CLI for running specific tests, making it easier to validate new features and bug fixes.
