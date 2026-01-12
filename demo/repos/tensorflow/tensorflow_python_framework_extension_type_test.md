# tensorflow.python.framework.extension_type_test.BrokenExtensionType and tensorflow.python.framework.type_spec_test.Foo Documentation

This document describes the `BrokenExtensionType` class and `Foo` class, which are part of the `tensorflow.python.framework.extension_type_test` and `tensorflow.python.framework.type_spec_test` modules, respectively. These classes are used in testing `ExtensionType` and `TypeSpec` functionalities.

## Core Functionality

*   **BrokenExtensionType:** A simple extension type with a custom `TypeSpec`. It is designed to test custom `TypeSpec` implementations.
*   **Foo:** A subclass of `TwoCompositesSpec`, used for testing purposes related to `TypeSpec`.

## Relationship to other components

*   `BrokenExtensionType` inherits from `extension_type.ExtensionType`.
*   `BrokenExtensionType.Spec` inherits from `type_spec.BatchableTypeSpec`.
*   `Foo` inherits from `TwoCompositesSpec`

