## 1. Theme Configuration

- [ ] 1.1 Create or update `lib/config.dart` (or similar file) to define the `AppColors.light` ("AI Minimalism") and `AppColors.dark` ("Y3K Cyber-Noir") color palettes.
- [ ] 1.2 Create `ThemeProvider` extending `ChangeNotifier` to hold and toggle the `ThemeMode`.
- [ ] 1.3 Update `main.dart` to optionally inject and read `ThemeProvider` via `ChangeNotifierProvider` globally and configure `MaterialApp` with `theme` and `darkTheme`.

## 2. Screens Updated

- [ ] 2.1 Update `RegisterScreen` to include an `IconButton` to toggle the theme via `ThemeProvider`.
- [ ] 2.2 Update `ChatScreen` to include an `IconButton` in the `AppBar` to toggle the theme.
- [ ] 2.3 Ensure any hardcoded colors in both screens adapt to the new `Theme.of(context)` properties.

## 3. Chat Bubble Visuals

- [ ] 3.1 Refactor the chat bubble widget rendering in `ChatScreen` to query `Theme.of(context)` rather than static constants.
- [ ] 3.2 Update User Chat Bubble `BoxDecoration` to use a `LinearGradient` substituting flat colors.
- [ ] 3.3 Add a `BoxShadow` to the User Chat Bubble using the designated neon accent color to create the "ambient glow" simulated effect.
- [ ] 3.4 Audit app run to verify Light ("AI Minimalism") and Dark ("Y3K Cyber-Noir") palettes apply without visual regression.
