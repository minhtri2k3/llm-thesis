## ADDED Requirements

### Requirement: Theme Switching
The system SHALL provide a toggle mechanism on the RegisterScreen and ChatScreen to switch between Light ("AI Minimalism") and Dark ("Y3K Cyber-Noir") modes.

#### Scenario: User toggles from Light to Dark mode
- **WHEN** the user is on the ChatScreen in Light Mode and taps the theme toggle icon
- **THEN** the application's overall theme switches to Dark Mode immediately, updating all backgrounds, text, and chat bubbles to the "Y3K Cyber-Noir" palette.

### Requirement: Dark Mode Palette Application
The system SHALL use the "Y3K Cyber-Noir" colors when in Dark Mode.

#### Scenario: Visual elements update for Dark Mode
- **WHEN** Dark Mode is active
- **THEN** the main background is `#0C0C0C`, the Bot Chat Bubble is `#232323`, the User Chat Bubble is a neon gradient based on `#00FFC2` or `#FF1F8A`, and the text is `#F0EEE9`.

### Requirement: Light Mode Palette Application
The system SHALL use the "AI Minimalism" colors when in Light Mode.

#### Scenario: Visual elements update for Light Mode
- **WHEN** Light Mode is active
- **THEN** the main background is `#F0EEE9`, the Bot Chat Bubble is `#EFFFF8`, the User Chat Bubble is `#9ADBC6`, and the text is `#2D3436`.

### Requirement: Advanced Bubble Aesthetics
The system SHALL apply advanced visual treatments to User Chat Bubbles in Dark Mode to reflect a futuristic digital fashion aesthetic.

#### Scenario: Procedural gradient and ambient glow
- **WHEN** a User Chat Bubble is rendered in Dark Mode
- **THEN** it displays a subtle procedural gradient and an ambient glow via BoxShadow using the assigned neon accent color to simulate oceanic iridescence or digital glow.
