# x3650 Fan Development Instructions

Instructions for high-quality IBM System x3650 M5 IPMI Fan Control development.

## Project Context

- Latest Perl (App Router)
- INI for configuration files
- Perl Critic for linting
- Test::More for unit and functional tests

## Development Standards

### Architecture

- Main script for core logic
- IPMI binary for system interaction
- modules to separate concerns
- Configuration file for settings
- Logging for debugging and monitoring
- Error handling with croak and carp
- Unit tests for all modules
- Functional tests for end-to-end scenarios
- Functional tests for system compatibility testing
- Email notifications for critical events

### Coding Standards

- Use strict mode
- Follow naming conventions
- Write modular and reusable code
- Include POD documentation and comments
- Adhere to the DRY principle
- Write tests for all new features
- Use version control (Git) with meaningful commit messages
- Unit tests shall not use real IPMI commands
- Unit tests shall mock external dependencies
