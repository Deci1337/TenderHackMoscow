# Portal supplier components for TenderHack Moscow

This is a TenderHack Moscow prototype, not an official deployment of the Moscow supplier portal. The interface adapts existing search behavior to the actual supplied Portal Postavshikov component kit.

## Verified design source

User-owned Figma board: https://www.figma.com/board/YmpRGshnGPUqcyxagZGWcu/Portal-Postavshikov--catalog---Copy-?node-id=0-1

The original board was inaccessible; the user-owned copy subsequently resolved access. The completed implementation uses that verified copy, superseding the earlier approximation. Source screenshots and targeted node exports were inspected before implementation.

| Implemented element | Source node | Adaptation |
| --- | --- | --- |
| Portal logo | 1:3828 inside header 1:3781 | Direct SVG export, bundled locally with intrinsic proportions |
| Header | 1:3781 | White 80px header, blue controls and real logo; only existing working app actions retained |
| Primary button | 1:59467 | Rectangular red 128×48 minimum search action, white label, hover/disabled/focus states |
| Search field | 1:54850 | 48px white bordered field, 16px left inset, trailing search icon, autocomplete and clear action |
| Filled dropdown | 1:59384 | Pale-blue 48px sort selector with existing sort values, native keyboard behavior |
| Card family | 1:4138 | Pale-blue rectangular shell, inset white content, blue price/title hierarchy; adapted to actual search results, without auction features |
| Popup family | 1:2112 | Flat white 648px responsive dialog, pale-blue backdrop, blue close action, 56px desktop insets and separated footer |
| Typography / colors | 1:1238 / 1:6044 | Open Sans; exact main blue, red, gray-blue and pale-blue tokens |

Main tokens: blue `#264B82`, red `#DB2B21`, pale blue `#E7EEF7`, border `#D4DBE6`, text `#1A1A1A`. Supporting success/info/warning colors follow the source. Secondary actionable text uses a darker neutral than the kit's pale helper gray for readability.

Open Sans is bundled from https://github.com/google/fonts/tree/main/ofl/opensans under the SIL Open Font License included at `frontend/public/fonts/OFL-OpenSans.txt`. Variable font axes: weight 300–800, width 75–100 (default width retained). No external font or logo requests are required. Desktop catalog text uses the kit's larger scale: 40/52 heading, 20px result titles and 18/26 body. Small metadata remains subordinate. Mobile titles/metadata stack rather than compress into narrow columns.

## Preserved behavior and accessibility

Existing API contracts, search/autocomplete, profile selection, categories, sort, details, likes/dislikes, interest panel and pagination remain. No backend changes or new training/performance claims were added. Product titles are native buttons; dialogs trap keyboard focus, close with Escape and restore their trigger. Visible focus, readable feedback controls, mobile collapsing filters and reduced-motion preferences are retained.

Browser evidence uses fabricated fixtures intercepted at the existing API boundary. It verifies frontend behavior and layout, not a live backend, production data or measured business outcomes. The case PDF labels this boundary explicitly.

## Requested design reviews

The requested design-taste-frontend and frontend-design skills informed hierarchy, restraint, implementation and visual review. Their generic marketing hero/templates were not applied to this functional catalog. Design direction: civic procurement workspace; differentiation is the real portal header, controls and shell/content treatment. DFII design judgment: impact 3 + fit 5 + feasibility 5 + performance 4 − consistency risk 2 = 15; not a measured outcome.

The requested unslop workflow and its signs/tokens/refs/visuals references informed spacing, copy, icon consistency and responsive review. Unslop by Damir Sokolovsky ([@heydamir](https://x.com/heydamir)), https://heydamir.design/unslop, CC BY 4.0. No generated illustrations are used.

A provisional taste gate attempt could not launch its Chrome checker and could not lint the profile selector; its ERROR is recorded in external run evidence, not represented as a pass. Final evidence is the project build and actual focused Playwright interactions/screenshots against the implemented kit.
