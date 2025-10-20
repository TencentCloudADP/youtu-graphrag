/**
 * @license
 * Copyright 2023 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
/**
 * This is a basic implementation of an EventTarget, Event and CustomEvent.
 *
 * This is not fully spec compliant (e.g. validation),
 * but should work well enough for our use cases.
 *
 * @see https://dom.spec.whatwg.org/#eventtarget
 * @see https://dom.spec.whatwg.org/#event
 * @see https://dom.spec.whatwg.org/#customevent
 */
export interface EventTargetShimMeta {
    /**
     * The event target parent represents the previous event target for an event
     * in capture phase and the next event target for a bubbling event.
     * Note that this is not the element parent
     */
    __eventTargetParent: EventTarget | undefined;
    /**
     * The host event target/element of this event target, if this event target
     * is inside a Shadow DOM.
     */
    __host: EventTarget | undefined;
}
declare const EventTargetShimWithRealType: typeof EventTarget;
export { EventTargetShimWithRealType as EventTarget, EventTargetShimWithRealType as EventTargetShim, };
declare const EventShimWithRealType: typeof Event;
declare const CustomEventShimWithRealType: typeof CustomEvent;
export { EventShimWithRealType as Event, EventShimWithRealType as EventShim, CustomEventShimWithRealType as CustomEvent, CustomEventShimWithRealType as CustomEventShim, };
//# sourceMappingURL=events.d.ts.map