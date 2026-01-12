# src_vs Module Documentation

## Overview

The `src_vs` module serves as the core API layer for the Monaco Editor integration within the broader VS Code ecosystem. It provides a set of interfaces and classes that define how the editor interacts with various language features, editor configurations, and UI elements. This module essentially exposes the necessary components for extending and customizing the Monaco Editor's behavior.

## Architecture

The `src_vs` module can be viewed as a collection of interfaces and classes that define the contract between the Monaco Editor and its clients. It doesn't contain concrete implementations but rather specifies the structure and behavior of various editor features. The architecture can be represented as follows:

```mermaid
classDiagram
    direction LR
    class ICommandDescriptor {
        id: string
        run: ICommandHandler
    }
    class ICodeEditorOpener {
        openCodeEditor(source: ICodeEditor, resource: Uri, selectionOrPosition: IRange | IPosition): boolean | Promise<boolean>
    }
    class NewSymbolNamesProvider {
        provideNewSymbolNames(model: editor.ITextModel, range: IRange, triggerKind: NewSymbolNameTriggerKind, token: CancellationToken): ProviderResult<NewSymbolName[]>
    }
    class SignatureHelpProvider {
        signatureHelpTriggerCharacters?: ReadonlyArray<string>
        provideSignatureHelp(model: editor.ITextModel, position: Position, token: CancellationToken, context: SignatureHelpContext): ProviderResult<SignatureHelpResult>
    }
    class KeyMod {
        static CtrlCmd: number
        static Shift: number
        static Alt: number
        static WinCtrl: number
        static chord(firstPart: number, secondPart: number): number
    }
    class DeclarationProvider {
        provideDeclaration(model: editor.ITextModel, position: Position, token: CancellationToken): ProviderResult<Definition | LocationLink[]>
    }
    class ReferenceProvider {
        provideReferences(model: editor.ITextModel, position: Position, context: ReferenceContext, token: CancellationToken): ProviderResult<Location[]>
    }
    class Token {
        offset: number
        type: string
        language: string
    }
    class TokensProviderFactory {
        create(): ProviderResult<TokensProvider | EncodedTokensProvider | IMonarchLanguage>
    }
    class IBaseMouseTarget {
        element: HTMLElement | null
        position: Position | null
        mouseColumn: number
        range: Range | null
    }
    class IMirrorTextModel {
        version: number
    }
    class DocumentFormattingEditProvider {
        provideDocumentFormattingEdits(model: editor.ITextModel, options: FormattingOptions, token: CancellationToken): ProviderResult<TextEdit[]>
    }
    class MultiDocumentHighlight {
        uri: Uri
        highlights: DocumentHighlight[]
    }
    class MultiDocumentHighlightProvider {
        provideMultiDocumentHighlights(primaryModel: editor.ITextModel, position: Position, otherModels: editor.ITextModel[], token: CancellationToken): ProviderResult<Map<Uri, DocumentHighlight[]>>
    }
    class InternalEditorScrollbarOptions {
        arrowSize: number
        vertical: ScrollbarVisibility
        horizontal: ScrollbarVisibility
    }
    class RenameProvider {
        provideRenameEdits(model: editor.ITextModel, position: Position, newName: string, token: CancellationToken): ProviderResult<WorkspaceEdit & Rejection>
    }
    class DocumentSymbolProvider {
        provideDocumentSymbols(model: editor.ITextModel, token: CancellationToken): ProviderResult<DocumentSymbol[]>
    }
    class ImplementationProvider {
        provideImplementation(model: editor.ITextModel, position: Position, token: CancellationToken): ProviderResult<Definition | LocationLink[]>
    }
    class IMarker {
        owner: string
        resource: Uri
        severity: MarkerSeverity
        message: string
    }
    class DocumentRangeFormattingEditProvider {
        provideDocumentRangeFormattingEdits(model: editor.ITextModel, range: Range, options: FormattingOptions, token: CancellationToken): ProviderResult<TextEdit[]>
    }
    class CompletionItemProvider {
        provideCompletionItems(model: editor.ITextModel, position: Position, context: CompletionContext, token: CancellationToken): ProviderResult<CompletionList>
    }
    class EditorWrappingInfo {
        isDominatedByLongLines: boolean
        isWordWrapMinified: boolean
        isViewportWrapping: boolean
        wrappingColumn: number
    }
    class IExpandedMonarchLanguageRule {
        regex?: string | RegExp
        action?: IMonarchLanguageAction
        include?: string
    }
    class CodeActionProviderMetadata {
        providedCodeActionKinds?: readonly string[]
    }
    class TypeDefinitionProvider {
        provideTypeDefinition(model: editor.ITextModel, position: Position, token: CancellationToken): ProviderResult<Definition | LocationLink[]>
    }
    class LinkedEditingRangeProvider {
        provideLinkedEditingRanges(model: editor.ITextModel, position: Position, token: CancellationToken): ProviderResult<LinkedEditingRanges>
    }
    class CodeLensProvider {
        provideCodeLenses(model: editor.ITextModel, token: CancellationToken): ProviderResult<CodeLensList>
    }
    class IExpandedMonarchLanguageAction {
        group?: IMonarchLanguageAction[]
        cases?: Object
        token?: string
        next?: string
    }
    class LanguageConfiguration {
        comments?: CommentRule
        brackets?: CharacterPair[]
        wordPattern?: RegExp
    }
    class InternalEditorRenderLineNumbersOptions {
        renderType: RenderLineNumbersType
        renderFn: ((lineNumber: number) => string) | null
    }
    class Hover {
        contents: IMarkdownString[]
        range?: IRange
    }
    class CodeActionProvider {
        provideCodeActions(model: editor.ITextModel, range: Range, context: CodeActionContext, token: CancellationToken): ProviderResult<CodeActionList>
    }
    class CommentThreadRevealOptions {
        preserveFocus: boolean
        focusReply: boolean
    }
    class IMouseTargetOverviewRuler {
        type: MouseTargetType.OVERVIEW_RULER
    }
    class HoverProvider {
        provideHover(model: editor.ITextModel, position: Position, token: CancellationToken, context?: HoverContext<THover>): ProviderResult<THover>
    }
    class DefinitionProvider {
        provideDefinition(model: editor.ITextModel, position: Position, token: CancellationToken): ProviderResult<Definition | LocationLink[]>
    }
    class IEditorOption {
        id: K
        name: string
        defaultValue: V
    }
    class FoldingRangeProvider {
        provideFoldingRanges(model: editor.ITextModel, context: FoldingContext, token: CancellationToken): ProviderResult<FoldingRange[]>
    }
    class OnTypeFormattingEditProvider {
        autoFormatTriggerCharacters: string[]
        provideOnTypeFormattingEdits(model: editor.ITextModel, position: Position, ch: string, options: FormattingOptions, token: CancellationToken): ProviderResult<TextEdit[]>
    }
    class DocumentSemanticTokensProvider {
        getLegend(): SemanticTokensLegend
        provideDocumentSemanticTokens(model: editor.ITextModel, lastResultId: string | null, token: CancellationToken): ProviderResult<SemanticTokens | SemanticTokensEdits>
    }
    class DocumentHighlightProvider {
        provideDocumentHighlights(model: editor.ITextModel, position: Position, token: CancellationToken): ProviderResult<DocumentHighlight[]>
    }
    class SelectionRangeProvider {
        provideSelectionRanges(model: editor.ITextModel, positions: Position[], token: CancellationToken): ProviderResult<SelectionRange[][]>
    }
    class InlayHintsProvider {
        provideInlayHints(model: editor.ITextModel, range: Range, token: CancellationToken): ProviderResult<InlayHintList>
    }
    class CancellationTokenSource {
        token: CancellationToken
        cancel(): void
        dispose(cancel?: boolean): void
    }
    class DocumentRangeSemanticTokensProvider {
        getLegend(): SemanticTokensLegend
        provideDocumentRangeSemanticTokens(model: editor.ITextModel, range: Range, token: CancellationToken): ProviderResult<SemanticTokens>
    }
    class DocumentColorProvider {
        provideDocumentColors(model: editor.ITextModel, token: CancellationToken): ProviderResult<IColorInformation[]>
        provideColorPresentations(model: editor.ITextModel, colorInfo: IColorInformation, token: CancellationToken): ProviderResult<IColorPresentation[]>
    }
    class ILinkOpener {
        open(resource: Uri): boolean | Promise<boolean>
    }
    class Environment {
        globalAPI?: boolean
        baseUrl?: string
        getWorker?(workerId: string, label: string): Promise<Worker> | Worker
    }
    class CommentAuthorInformation {
        name: string
        iconPath?: UriComponents
    }
    class IEditorZoom {
        onDidChangeZoomLevel: IEvent<number>
        getZoomLevel(): number
        setZoomLevel(zoomLevel: number): void
    }
    class ILanguagePack {
        hash: string
        label: string | undefined
        extensions: { readonly extensionIdentifier: { readonly id: string; readonly uuid?: string }; readonly version: string; }[]
        translations: Record<string, string | undefined>
    }




```

## Sub-modules Functionality

The `src_vs` module is further divided into several sub-modules, each responsible for a specific aspect of the editor's functionality:

*   **`src_vs_editor`**: This sub-module (containing 607 components) likely deals with core editor functionalities such as text manipulation, cursor movement, and basic editor commands. See [src_vs_editor.md](src_vs_editor.md) for more details.
*   **`src_vs_workbench`**:  With 2854 components, this sub-module probably encompasses the workbench features surrounding the editor, including panels, menus, and overall application structure. See [src_vs_workbench.md](src_vs_workbench.md) for more details.
*   **`src_vs_platform`**: This sub-module (containing 290 components) likely provides platform-specific services and abstractions, such as file system access, operating system integration, and UI theming. See [src_vs_platform.md](src_vs_platform.md) for more details.
*   **`src_vscode_dts`**: This sub-module (containing 83 components) likely provides the TypeScript definition files for the VS Code API, enabling type checking and autocompletion for extension developers. See [src_vscode_dts.md](src_vscode_dts.md) for more details.
*   **`src_vs_base`**:  This sub-module (containing 109 components) likely provides fundamental data structures, utility functions, and base classes used throughout the VS Code codebase. See [src_vs_base.md](src_vs_base.md) for more details.
*   **`src_typings`**:  This sub-module (containing 4 components) likely defines basic type definitions used across the VS Code project. See [src_typings.md](src_typings.md) for more details.
*   **`src_vs_code`**: This sub-module (containing 14 components) likely contains code specific to VS Code, potentially related to branding or product-specific features. See [src_vs_code.md](src_vs_code.md) for more details.
*   **`src_vs_server`**: This sub-module (containing 2 components) might handle server-side functionalities or communication with external services. See [src_vs_server.md](src_vs_server.md) for more details.

## Core Components

The `src_vs` module exposes a wide range of components, including interfaces and classes, that define various aspects of the Monaco Editor.

*   **`ICommandDescriptor`**: Defines the structure for editor commands, including their unique identifier and the callback function to execute.
*   **`ICodeEditorOpener`**:  Interface for opening code editors, allowing navigation to definitions and references in other files.
*   **`NewSymbolNamesProvider`**: Provides new symbol names for rename operations.
*   **`SignatureHelpProvider`**: Provides signature help for functions and methods.
*   **`KeyMod`**:  A class for defining keybindings and keyboard shortcuts.
*   **`DeclarationProvider`**: Provides the declaration of a symbol at a given position.
*   **`ReferenceProvider`**:  Provides references to a symbol throughout the project.
*   **`Token`**: Represents a token in the editor, with information about its offset, type, and language.
*   **`TokensProviderFactory`**:  A factory for creating token providers for syntax highlighting.
*   **`IBaseMouseTarget`**:  Interface for mouse target information in the editor.
*   **`IMirrorTextModel`**: Interface representing a mirror of a text model.
*   **`DocumentFormattingEditProvider`**: Provides formatting edits for an entire document.
*   **`MultiDocumentHighlight`**: Represents highlights across multiple documents.
*   **`MultiDocumentHighlightProvider`**: Provides highlights across multiple documents.
*   **`InternalEditorScrollbarOptions`**: Defines options for the editor's scrollbars.
*   **`RenameProvider`**:  Provides rename refactoring functionality.
*   **`DocumentSymbolProvider`**: Provides document symbols (e.g., classes, functions) for the outline view.
*   **`ImplementationProvider`**: Provides the implementation of a symbol.
*   **`IMarker`**: Represents a marker (e.g., error, warning) in the editor.
*   **`DocumentRangeFormattingEditProvider`**: Provides formatting edits for a specific range in a document.
*   **`CompletionItemProvider`**: Provides completion items for autocompletion.
*   **`EditorWrappingInfo`**: Provides information about editor wrapping.
*   **`IExpandedMonarchLanguageRule`**:  Interface for expanded Monarch language rules (used for syntax highlighting).
*   **`CodeActionProviderMetadata`**: Metadata for code action providers.
*   **`TypeDefinitionProvider`**: Provides the type definition of a symbol.
*   **`LinkedEditingRangeProvider`**: Provides ranges that can be edited together.
*   **`CodeLensProvider`**: Provides CodeLens information (inline actions).
*   **`IExpandedMonarchLanguageAction`**: Interface for expanded Monarch language actions.
*   **`LanguageConfiguration`**: Defines the configuration for a language (e.g., comments, brackets).
*   **`InternalEditorRenderLineNumbersOptions`**: Defines options for rendering line numbers.
*   **`Hover`**: Represents a hover in the editor.
*   **`CodeActionProvider`**: Provides code actions (e.g., quick fixes, refactorings).
*   **`CommentThreadRevealOptions`**: Options for revealing comment threads.
*   **`IMouseTargetOverviewRuler`**: Interface for mouse target information in the overview ruler.
*   **`HoverProvider`**: Provides hover information.
*   **`DefinitionProvider`**: Provides the definition of a symbol.
*   **`IEditorOption`**: Interface for editor options.
*   **`FoldingRangeProvider`**: Provides folding ranges for code folding.
*   **`OnTypeFormattingEditProvider`**: Provides formatting edits as the user types.
*   **`DocumentSemanticTokensProvider`**: Provides semantic tokens for syntax highlighting.
*   **`DocumentHighlightProvider`**: Provides document highlights.
*   **`SelectionRangeProvider`**: Provides selection ranges.
*   **`InlayHintsProvider`**: Provides inlay hints (inline hints in the editor).
*   **`CancellationTokenSource`**:  A class for managing cancellation tokens.
*   **`DocumentRangeSemanticTokensProvider`**: Provides semantic tokens for a specific range.
*   **`DocumentColorProvider`**: Provides color information for a document.
*   **`ILinkOpener`**: Interface for opening links.
*   **`Environment`**:  Interface for environment configuration.
*   **`CommentAuthorInformation`**: Information about a comment author.
*   **`IEditorZoom`**: Interface for editor zoom level.
*   **`ILanguagePack`**: Interface for language pack information.


These components are used by other modules within the VS Code ecosystem to provide a rich editing experience.
