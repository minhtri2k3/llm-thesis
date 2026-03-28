## Why

The user wants an updated, modern aesthetic for their AI fashion assistant, capable of appealing to dual-persona demographics. Providing a clear toggle between Light ("AI Minimalism") and Dark ("Y3K Cyber-Noir") themes gives the user more control while improving the overall visual fidelity, trustworthiness, and futuristic feel of the application.

## What Changes

- Add a dark/light mode toggle switch to both the RegisterScreen and ChatScreen. 
- Expand and update color palettes for both modes according to the specific design specifications: "AI Minimalism" and "Y3K Cyber-Noir".
- Introduce advanced visual treatments to chat bubbles, including procedural gradients and an "ambient glow" effect.
- Wire theme state management via `provider` to automatically apply the chosen theme layout app-wide.

## Capabilities

### New Capabilities
- `theme-management`: A unified theme management capability supporting toggling between light and dark modes with comprehensive custom color mappings and styling effects.

### Modified Capabilities


## Impact

- **UI/UX**: Register and Chat screens will get an updated top app bar including the theme toggle icon. Entire application surface and component colors will change.
- **State**: A new ThemeProvider (or equivalent theme notifier) will be needed to broadcast the current selected theme mode via `provider`.
- **Performance**: Very low impact. The subtle gradient and glow effect uses standard Flutter `BoxDecoration` and `BoxShadow`, which are performant.
