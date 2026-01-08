# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.3.0] - 2026-01-06 🚀

### Added
- Pipeline execution constraints for better control over pipeline runs
- Integration with Langfuse for observability and monitoring
- RAGAS metrics integration for RAG evaluation
- Modal components for improved UI interactions
- Block configuration view for enhanced block setup
- Generator view for better visualization

### Changed
- Refactored codebase with Pydantic for improved data validation and type safety
- Enhanced custom components theming

### Fixed
- Job cancellation bug that prevented proper pipeline stopping
- Langfuse dataset naming issues

## [1.2.0] - 2025-11-17 🚀

### Added
- Model/Embed UI: Ability to create, set up, and test various models and embeddings directly in the application
- New 'Seeders' block type for directly loading and chunking content from Markdown files
- Q&A generation template for direct generation of Q&A pairs from Markdown files
- Docker support: Application is now fully runnable on Docker for simplified setup and deployment
- Model selection directly in blocks (pulled from configuration)
- Validation of seeds before running a pipeline

### Changed
- Enhanced block configuration interface with integrated model and embedding selection capabilities
- Official website moved from GitHub Pages to datagenflow.com with improved documentation and guides

### Fixed
- Pipeline status and error alignment improvements
- Various bugs and stability improvements

## [1.1.0] - 2025-10-29 🚀

### Added
- Integrated LiteLLM for robust multi-provider stability, structured output, and providers management
- Three new Pipeline Templates (JSON Generation, Text Classification, Q&A Generation)
- Jinja2 templating support for dynamic prompts in UI blocks
- New website with feature guides and documentation
- Switch table/single view for the Review page
- Display config in the Review page
- Debug pipeline script for local testing/debugging

### Changed
- Improved Pipeline Editor with enhanced block visualization and new auto-layout
- Improve usability of config forms with better defaults and descriptions

### Fixed
- Various bugs and stability issues

## [1.0.0] - Initial Release 🎉

### Added
- Core pipeline execution engine with block-based architecture
- Visual pipeline editor with React Flow
- REST API for pipeline execution
- Template system for common use cases

[1.3.0]: https://github.com/nicofretti/DataGenFlow/compare/release-v1.2.0...release-v1.3.0
[1.2.0]: https://github.com/nicofretti/DataGenFlow/compare/release-v1.1.0...release-v1.2.0
[1.1.0]: https://github.com/nicofretti/DataGenFlow/compare/release...release-v1.1.0
[1.0.0]: https://github.com/nicofretti/DataGenFlow/releases/tag/release
