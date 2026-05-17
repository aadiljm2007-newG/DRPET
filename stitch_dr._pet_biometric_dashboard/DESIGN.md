---
name: Zen Minimalist for Dr. PET
colors:
  surface: '#f7f9fb'
  surface-dim: '#d8dadc'
  surface-bright: '#f7f9fb'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f2f4f6'
  surface-container: '#eceef0'
  surface-container-high: '#e6e8ea'
  surface-container-highest: '#e0e3e5'
  on-surface: '#191c1e'
  on-surface-variant: '#464555'
  inverse-surface: '#2d3133'
  inverse-on-surface: '#eff1f3'
  outline: '#777587'
  outline-variant: '#c7c4d8'
  surface-tint: '#4d44e3'
  primary: '#3525cd'
  on-primary: '#ffffff'
  primary-container: '#4f46e5'
  on-primary-container: '#dad7ff'
  inverse-primary: '#c3c0ff'
  secondary: '#515f74'
  on-secondary: '#ffffff'
  secondary-container: '#d5e3fd'
  on-secondary-container: '#57657b'
  tertiary: '#7e3000'
  on-tertiary: '#ffffff'
  tertiary-container: '#a44100'
  on-tertiary-container: '#ffd2be'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#e2dfff'
  primary-fixed-dim: '#c3c0ff'
  on-primary-fixed: '#0f0069'
  on-primary-fixed-variant: '#3323cc'
  secondary-fixed: '#d5e3fd'
  secondary-fixed-dim: '#b9c7e0'
  on-secondary-fixed: '#0d1c2f'
  on-secondary-fixed-variant: '#3a485c'
  tertiary-fixed: '#ffdbcc'
  tertiary-fixed-dim: '#ffb695'
  on-tertiary-fixed: '#351000'
  on-tertiary-fixed-variant: '#7b2f00'
  background: '#f7f9fb'
  on-background: '#191c1e'
  surface-variant: '#e0e3e5'
typography:
  display:
    fontFamily: Inter
    fontSize: 48px
    fontWeight: '300'
    lineHeight: '1.2'
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '500'
    lineHeight: '1.3'
    letterSpacing: -0.01em
  headline-lg-mobile:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '500'
    lineHeight: '1.3'
    letterSpacing: -0.01em
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: '1.6'
    letterSpacing: 0em
  label-caps:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '600'
    lineHeight: '1'
    letterSpacing: 0.1em
  stats-lg:
    fontFamily: Inter
    fontSize: 40px
    fontWeight: '200'
    lineHeight: '1'
    letterSpacing: -0.03em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  unit: 8px
  container-max-width: 1280px
  gutter: 32px
  margin-safe: 40px
  section-gap: 80px
---

## Brand & Style

This design system is defined by **Extreme Minimalism** and **Kinetic Elegance**. It is designed for high-stakes pet health and behavioral intelligence, requiring an atmosphere of calm, clinical precision, and sophisticated warmth. The brand personality is "The Quiet Observer"—intelligent, unobtrusive, and deeply reliable.

The visual style leverages **Minimalism** with a focus on "Atmospheric Depth." By removing harsh borders and traditional boxiness, the UI relies on negative space and soft light-source shadows to define hierarchy. Motion is not decorative but functional, utilizing subtle ease-in-out transitions to provide a sense of organic responsiveness, echoing the rhythmic nature of life.

## Colors

The palette is monochromatic with high-intent accents. 
- **Primary Indigo (#4F46E5):** Reserved exclusively for critical data points, active behavioral spikes, and primary calls to action. It should be used sparingly to maintain its emotional impact.
- **Grays & Slates:** A spectrum of soft off-whites and deep slates provide the structural foundation.
- **Dark Mode:** Transitions from a clinical white to a "Deep Slate Workspace" (#0F172A), reducing eye strain while maintaining high-end professional aesthetics.

## Typography

The typography system uses **Inter** to achieve a utilitarian yet elegant feel. 
- **Tracking:** Elegant, wider tracking is applied to labels and small caps to increase legibility and "airiness." 
- **Weight Pairing:** High contrast between light weights for large displays and medium/bold weights for functional labels.
- **Scale:** Emphasize generous line heights (1.6x for body) to ensure the interface never feels "dense" or crowded.

## Layout & Spacing

The design system employs a **Fluid-Fixed Hybrid Grid**. Content is centered within a 1280px container on desktop, but the background "atmosphere" (shadows and blurs) remains fluid to the edge of the viewport.

- **Generous White Space:** Use a base 8px scale, but favor larger increments (40px, 80px) for section vertical spacing to evoke "Zen" clarity.
- **Mobile Reflow:** On mobile devices, margins reduce to 20px, and section gaps compress to 40px. Components should stack vertically, maintaining the soft shadow depth to separate distinct modules without the need for horizontal rules.

## Elevation & Depth

Hierarchy is established through **High-Latitude Shadows** rather than borders.
- **Surface Level 0:** The main workspace background (Pure White or Deep Slate).
- **Surface Level 1 (Floating Cards):** Uses the signature shadow: `0 10px 40px rgba(0,0,0,0.03)`. This creates a subtle lift that feels like paper floating over a surface.
- **Interaction Depth:** On hover or active state, the shadow should slightly expand and soften (increase blur to 60px) to simulate the element moving closer to the user.
- **Zero-Border Policy:** Strictly avoid solid 1px borders. Use tonal shifts in background color (e.g., a 2% darker gray) if a boundary is absolutely necessary.

## Shapes

The shape language is **Softly Geometric**. 
- Standard components (buttons, input fields) use a 0.5rem (8px) radius. 
- Large containers and dashboard modules use a 1rem (16px) radius to soften the technical nature of the data. 
- Avoid sharp 0px corners entirely to maintain the "Zen" approachable aesthetic.

## Components

- **Buttons:** Primary buttons use a solid Indigo fill with no border. Secondary buttons use a light-gray ghost style that only reveals a shadow on hover.
- **Metrics/Chips:** Use a "Pill" shape with a background color only 5% different from the surface to indicate status without being loud.
- **Inputs:** Clean, bottom-aligned labels. The input field itself is a slightly tinted surface (Level 0.5) with no border; it "rises" via shadow when focused.
- **Cards:** The central container. No borders. Padding should be generous (min 32px).
- **Data Visualizations:** Line graphs should use a "Kinetic" stroke—variable width and soft easing on the path animations. Critical pet health spikes are the only elements allowed to use the Primary Indigo.