## Context

The Clothie app currently uses a static dark theme defined in `main.dart`. The user requested to add a light theme ("AI Minimalism") and an updated dark theme ("Y3K Cyber-Noir") along with a toggle switch on both the `RegisterScreen` and `ChatScreen`. Additionally, the chat bubbles require visual upgrades such as a procedural gradient and an ambient glow to fit the digital fashion aesthetic.

## Goals / Non-Goals

**Goals:**
- Implement stateful theme switching that persists or applies instantaneously across the app using `provider`.
- Create a configuration file or a dedicated theme class (`app_theme.dart`) isolating the new colors.
- Upgrade the visual treatments for chat bubbles to include gradients and shadow glows.
- Provide a clear, accessible toggle in the AppBar of both Register and Chat screens.

**Non-Goals:**
- Extensive refactoring of unrelated widgets.
- Adding animations for the transition itself (unless provided seamlessly by `Theme` defaults).
- Allowing custom color pickers; the app will strictly stick to the predefined "AI Minimalism" and "Y3K Cyber-Noir" palettes.

## Decisions

- **State Management**: We will use `provider` with `ChangeNotifier` (`ThemeProvider`) to track `ThemeMode.light` versus `ThemeMode.dark`. Currently, the app uses `provider`, making this the most native fit without introducing new dependencies.
- **Theme Configurations**: We will keep general config variables in `config.dart`, but we will group the new palette into structured static maps or dedicated palette classes `AppColors.light` and `AppColors.dark` to make theme consumption cleaner and more modular.
- **Chat Bubble Gradients & Glowing**: For the "ambient glow" and gradient, we will use a `BoxDecoration` inside the message widget with a `LinearGradient` (shifting from the primary neon color to a slightly darker teal shade) and a `BoxShadow` with the same color, offset `(0,0)`, and high blur radius to simulate light emission.

## Risks / Trade-offs

- **[Risk] Rendering Performance with Glows**: Heavy usage of large spread `BoxShadow` on lists can impact scrolling performance on web or less-powerful devices.
  - *Mitigation*: The ambient glow will be tuned (moderate blur radius) to ensure `Canvas` rendering doesn't severely drop framerate. Performance profiling is recommended.
- **[Risk] Hardcoded colors breaking under different ThemeModes**: Existing screens might rely on hardcoded `config.dart` colors rather than querying the context.
  - *Mitigation*: We will review `ChatScreen` and `RegisterScreen` to pipe the appropriate colors dynamically based on the current `ThemeMode` via `Theme.of(context)` or our `ThemeProvider`.
