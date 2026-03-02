# Design Principles

A reference for building interfaces that communicate clearly and stay out of the way. Grounded in the work of Vignelli, Reichenstein, Rams, Tufte, Saffer, Krug, and foundational HCI research.

---

## 1. Typography

> "Web design is 95% typography."
> — Oliver Reichenstein, *Information Architects* (2006)

Typography is not decoration — it is the primary interface. When type hierarchy is correct, the UI barely needs anything else.

**Rules:**
- **Baseline:** 16px body text minimum. Below this, readability degrades on screens.
- **Line height:** 1.4–1.6 for body text. Tighter (1.1–1.25) for headings.
- **Measure:** 45–75 characters per line (10–15 words). Wider lines cause re-reading; narrower lines break rhythm.
- **Scale:** Use a limited set of sizes (5–7 steps). Each step must be visibly distinct from its neighbors — if you have to squint to tell two sizes apart, merge them.
- **Weight as hierarchy:** Weight differences (300 vs 600) communicate importance faster than size differences. Use weight before reaching for size.
- **Two typefaces maximum.** One serif, one sans-serif. A third typeface is almost never justified.

**Test:** Cover every element except the text. Can you still tell what's a heading, what's body, what's metadata? If not, the type hierarchy is failing.

---

## 2. Color

> "Black is black, red is color."
> — Massimo Vignelli

The 60-30-10 rule: 60% dominant (background/surface), 30% secondary (text, borders, structure), 10% accent (calls to action, active states).

**Rules:**
- **Accent scarcity:** The accent color must remain rare. If 30% of the viewport is accent-colored during normal use, it has lost its power to direct attention.
- **One accent role:** Each accent color gets one semantic job. If teal means "interactive," it should not also mean "decorative." If warm means "rating," it should not also mean "border."
- **Sufficient contrast:** WCAG AA minimum (4.5:1 for text, 3:1 for large text and UI components). This is not optional — it is the floor.
- **Dark mode is not inverted light mode.** Reduce contrast slightly (pure white on black is harsh). Muted colors need re-checking; they often fail contrast requirements in dark mode.

**Test:** Squint at the page. The accent color should be the first thing your eye finds. If multiple things compete, reduce accent usage until one wins.

---

## 3. Visual Hierarchy

> "Making pages scannable: it's not just important, it's everything."
> — Steve Krug, *Don't Make Me Think* (2000)

Krug's three traits of visual hierarchy:
1. **Prominence reflects importance.** The most important element must be the most visually prominent. If everything is bold, nothing is bold.
2. **Grouping reflects relationship.** Things that work together must look like they belong together — through proximity, shared styling, or enclosure.
3. **Nesting reflects hierarchy.** Parent–child relationships must be visually obvious through indentation, size reduction, or containment.

**Rules:**
- **Three tiers maximum** for any set of controls. Primary (always visible, strong presence), secondary (visible but receding), contextual (hidden until needed or placed outside the primary flow).
- **No two elements should have identical visual weight unless they have identical importance.** Buttons, filters, toggles — if they all look the same, the user must read every label to find what they want.
- **Whitespace is structure.** It is not "empty space to fill" — it is the separator between groups. More whitespace between groups than within groups.

**Test:** Show the interface to someone for 5 seconds, then take it away. Ask them what the primary action is. If they can't answer, the hierarchy is broken.

---

## 4. Information Density

> "Every bit of ink on a graphic requires a reason. And nearly always that reason should be that the ink presents new information."
> — Edward Tufte, *The Visual Display of Quantitative Information* (1983)

**Tufte's data-ink ratio:** Maximize the share of ink (or pixels) devoted to actual data. Remove everything that doesn't carry information.

**Rules:**
- **Smallest effective difference.** Make visual distinctions just large enough to be perceived — no larger. A 1px border separates as effectively as a 3px border, with less visual noise.
- **No chartjunk.** Decorative gradients, shadows for shadows' sake, borders that don't separate anything — these are noise that competes with signal.
- **Redundant encoding is waste.** If a number already says "9.2", you don't also need a star icon, a color fill, and a tooltip repeating it.
- **Labels over legends.** Put labels directly on the data (inline), not in a separate key that requires the eye to jump back and forth.

**Test:** Remove an element. Does the user lose information? If not, the element was noise. Keep removing until something breaks.

---

## 5. Interaction Design

> "A microinteraction is a contained product moment that revolves around a single use case."
> — Dan Saffer, *Microinteractions* (2013)

Saffer's framework for evaluating any interaction:
1. **Trigger** — What initiates it? (User click, system event, state change)
2. **Rules** — What happens? (The logic, the state change)
3. **Feedback** — How does the user know it happened? (Visual change, animation, text update)
4. **Loops & Modes** — Does it repeat? Change over time?

**Rules:**
- **Animation must communicate state.** A transition that says "this panel is opening" is useful. A transition that says "look, I can animate" is not.
- **Duration:** 150–300ms for UI transitions. Under 100ms feels instant (skip the animation). Over 500ms feels sluggish.
- **Easing:** Use ease-out for entrances (fast start, gentle stop) and ease-in for exits (gentle start, fast departure). Linear motion feels robotic.
- **`prefers-reduced-motion` is mandatory.** Every animation must have a reduced-motion alternative. This is not progressive enhancement — it is accessibility.

**Test:** Disable all animations. Does the interface still work and communicate clearly? If not, you're using animation as a crutch for missing visual hierarchy.

---

## 6. Cognitive Load (Hick's Law)

> "The time it takes to make a decision increases with the number and complexity of choices."
> — William Edmund Hick (1952), refined by Ray Hyman

**Hick's Law:** Decision time = a + b × log₂(n+1), where n = number of equally probable choices.

**Rules:**
- **Reduce visible options.** If 80% of users use the default sort order, show the default and hide the alternatives behind a single trigger (dropdown, disclosure). Four always-visible buttons cost cognitive overhead even when ignored.
- **Progressive disclosure.** Show the minimum needed at each step. Filters → dropdown on demand. Advanced options → behind "more." Not every feature earns permanent screen presence.
- **Smart defaults.** Choose the right default so most users never need to change it. A filter that ships at "all" is a non-decision. A sort that ships at "best first" serves most use cases.
- **Group related choices.** Five filters feel like less than five filters if they're organized into two labeled groups.

**Test:** Count the number of decisions a new user must make before seeing content. Each decision is friction. Target: zero decisions for first content, progressive disclosure for refinement.

---

## 7. Motor Performance (Fitts's Law)

> "The time to acquire a target is a function of the distance to and size of the target."
> — Paul Fitts (1954)

**Fitts's Law:** Movement time = a + b × log₂(1 + D/W), where D = distance to target, W = width of target.

**Rules:**
- **44px minimum touch target** (Apple HIG) / **48dp** (Material Design). This is the floor for fingers. For mouse-only interfaces, 32px is acceptable but 44px is still better.
- **Padding counts.** A 12px text link with 16px padding on each side is a 44px target even though the text is small.
- **Edge and corner advantage.** Targets at screen edges are effectively infinite-width because the cursor stops at the edge. Sticky headers exploit this. Corner buttons get two infinite-width edges.
- **Group frequently-used targets.** Reduce the distance between common actions. Don't scatter related controls across the viewport.

**Test:** Use the interface with a finger on a small phone (320px wide). Can you hit every target without zooming? Can you avoid hitting the wrong target?

---

## 8. Unobtrusive Design

> "Good design is as little design as possible. Less, but better — because it concentrates on the essential aspects, and the products are not burdened with non-essentials. Back to purity, back to simplicity."
> — Dieter Rams, Principle #10

Also Rams' Principle #5: "Good design is unobtrusive. Products fulfilling a purpose are like tools. They are neither decorative objects nor works of art. Their design should therefore be both neutral and restrained, to leave room for the user's self-expression."

**Rules:**
- **Content dominates, chrome recedes.** Controls, navigation, and structural elements should be visually quieter than the content they serve. If the toolbar is the most prominent thing on screen, the hierarchy is inverted.
- **Earn every pixel.** Every border, shadow, icon, and color must justify its existence. "It looks bare without it" is not justification. "Users couldn't tell these groups apart without it" is.
- **No decoration disguised as function.** A gradient that aids readability (text over image) is functional. A gradient that "adds visual interest" is decoration.
- **Restraint is the default.** Start with nothing and add only what's necessary. Do not start with "standard UI components" and try to simplify later — you'll keep things that shouldn't exist.

**Test:** Describe the purpose of every visible element in one sentence. If you can't, or if the sentence is "it looks nice," remove it.

---

## 9. Decision Framework

Before adding or modifying any UI element, answer these questions:

| # | Question | If No... |
|---|----------|----------|
| 1 | Does this element carry information the user needs? | Remove it. |
| 2 | Does it have a clear hierarchy level (primary/secondary/contextual)? | Assign one. If everything is "primary," demote most of them. |
| 3 | Could it be text instead of a button/icon/widget? | Make it text. Text is always more scannable than icons. |
| 4 | If it's an icon, can users understand it without a label? | Add a label, or replace with text entirely. |
| 5 | Is the animation communicating a state change? | Remove the animation. |
| 6 | Does it pass the squint test? (Is hierarchy visible at low resolution?) | Increase contrast between hierarchy levels. |
| 7 | At the current accent usage, does accent still direct attention? | Reduce accent to fewer elements until it regains its power. |
| 8 | Can the user reach this target easily on mobile? (≥44px) | Increase the target size. |
| 9 | Is this visible by default, or could it be progressive disclosure? | Move it behind a trigger unless ≥50% of users need it immediately. |
| 10 | Does adding this increase the number of equi-prominent choices? | Differentiate it visually, or group/hide it. |

---

## 10. Sources

- Reichenstein, Oliver. "Web Design is 95% Typography." *iA*, 2006. https://ia.net/topics/the-web-is-all-about-typography-period
- Vignelli, Massimo. *The Vignelli Canon.* Lars Müller Publishers, 2010. https://www.vignelli.com/canon.pdf
- Tufte, Edward. *The Visual Display of Quantitative Information.* Graphics Press, 1983.
- Tufte, Edward. *Envisioning Information.* Graphics Press, 1990.
- Krug, Steve. *Don't Make Me Think.* New Riders, 2000 (3rd ed. 2014).
- Saffer, Dan. *Microinteractions: Designing with Details.* O'Reilly, 2013.
- Rams, Dieter. "Ten Principles for Good Design." https://www.vitsoe.com/us/about/good-design
- Hick, W.E. "On the Rate of Gain of Information." *Quarterly Journal of Experimental Psychology*, 4(1), 1952.
- Fitts, Paul. "The Information Capacity of the Human Motor System in Controlling the Amplitude of Movement." *Journal of Experimental Psychology*, 47(6), 1954.
- Apple Human Interface Guidelines. "Touchscreen Gestures: Target Sizes." https://developer.apple.com/design/human-interface-guidelines/
- Material Design Guidelines. "Touch Targets." https://m3.material.io/foundations/accessible-design/accessibility-basics
- 60-30-10 Color Rule. Interior design principle widely adapted for UI. Referenced in *Refactoring UI* by Wathan & Schoger, 2018.
