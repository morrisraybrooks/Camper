# feedback-no-live-preview-flips

> Don't temporarily invert conditions on the live camper dashboard to preview styles — the user sees and uses it meanwhile

Don't preview a style by temporarily flipping a condition in the live `camper.yaml` (e.g. orange-when-`off` to see the "on" look). On 2026-09-30 the user was tapping the Ceiling Fan badge during a ~1 min flip window, and their browser kept the flipped layout until refresh, so they reported the badge as "backwards".

**Why:** the dashboard is in active use; YAML dashboards stay cached in open browsers until a refresh, so a temporary flip can outlive the revert.
**How to apply:** preview by injecting the CSS into the badge's shadow root with the browser JS tool (no file change), or check it on a real state change. See [[project-camper-easytouch]].
