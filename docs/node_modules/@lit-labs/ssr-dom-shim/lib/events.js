/**
 * @license
 * Copyright 2023 Google LLC
 * SPDX-License-Identifier: BSD-3-Clause
 */
var __classPrivateFieldSet = (this && this.__classPrivateFieldSet) || function (receiver, state, value, kind, f) {
    if (kind === "m") throw new TypeError("Private method is not writable");
    if (kind === "a" && !f) throw new TypeError("Private accessor was defined without a setter");
    if (typeof state === "function" ? receiver !== state || !f : !state.has(receiver)) throw new TypeError("Cannot write private member to an object whose class did not declare it");
    return (kind === "a" ? f.call(receiver, value) : f ? f.value = value : state.set(receiver, value)), value;
};
var __classPrivateFieldGet = (this && this.__classPrivateFieldGet) || function (receiver, state, kind, f) {
    if (kind === "a" && !f) throw new TypeError("Private accessor was defined without a getter");
    if (typeof state === "function" ? receiver !== state || !f : !state.has(receiver)) throw new TypeError("Cannot read private member from an object whose class did not declare it");
    return kind === "m" ? f : kind === "a" ? f.call(receiver) : f ? f.value : state.get(receiver);
};
var _Event_cancelable, _Event_bubbles, _Event_composed, _Event_defaultPrevented, _Event_timestamp, _Event_propagationStopped, _Event_type, _Event_target, _Event_isBeingDispatched, _a, _CustomEvent_detail, _b;
const isCaptureEventListener = (options) => (typeof options === 'boolean' ? options : options?.capture ?? false);
// Event phases
const NONE = 0;
const CAPTURING_PHASE = 1;
const AT_TARGET = 2;
const BUBBLING_PHASE = 3;
// Shim the global EventTarget object
const EventTargetShim = class EventTarget {
    constructor() {
        this.__eventListeners = new Map();
        this.__captureEventListeners = new Map();
    }
    addEventListener(type, callback, options) {
        if (callback === undefined || callback === null) {
            return;
        }
        const eventListenersMap = isCaptureEventListener(options)
            ? this.__captureEventListeners
            : this.__eventListeners;
        let eventListeners = eventListenersMap.get(type);
        if (eventListeners === undefined) {
            eventListeners = new Map();
            eventListenersMap.set(type, eventListeners);
        }
        else if (eventListeners.has(callback)) {
            return;
        }
        const normalizedOptions = typeof options === 'object' && options ? options : {};
        normalizedOptions.signal?.addEventListener('abort', () => this.removeEventListener(type, callback, options));
        eventListeners.set(callback, normalizedOptions ?? {});
    }
    removeEventListener(type, callback, options) {
        if (callback === undefined || callback === null) {
            return;
        }
        const eventListenersMap = isCaptureEventListener(options)
            ? this.__captureEventListeners
            : this.__eventListeners;
        const eventListeners = eventListenersMap.get(type);
        if (eventListeners !== undefined) {
            eventListeners.delete(callback);
            if (!eventListeners.size) {
                eventListenersMap.delete(type);
            }
        }
    }
    dispatchEvent(event) {
        const composedPath = [this];
        let parent = this.__eventTargetParent;
        if (event.composed) {
            while (parent) {
                composedPath.push(parent);
                parent = parent.__eventTargetParent;
            }
        }
        else {
            // If the event is not composed and the event was dispatched inside
            // shadow DOM, we need to stop before the host of the shadow DOM.
            while (parent && parent !== this.__host) {
                composedPath.push(parent);
                parent = parent.__eventTargetParent;
            }
        }
        // We need to patch various properties that would either be empty or wrong
        // in this scenario.
        let stopPropagation = false;
        let stopImmediatePropagation = false;
        let eventPhase = NONE;
        let target = null;
        let tmpTarget = null;
        let currentTarget = null;
        const originalStopPropagation = event.stopPropagation;
        const originalStopImmediatePropagation = event.stopImmediatePropagation;
        Object.defineProperties(event, {
            target: {
                get() {
                    return target ?? tmpTarget;
                },
                ...enumerableProperty,
            },
            srcElement: {
                get() {
                    return event.target;
                },
                ...enumerableProperty,
            },
            currentTarget: {
                get() {
                    return currentTarget;
                },
                ...enumerableProperty,
            },
            eventPhase: {
                get() {
                    return eventPhase;
                },
                ...enumerableProperty,
            },
            composedPath: {
                value: () => composedPath,
                ...enumerableProperty,
            },
            stopPropagation: {
                value: () => {
                    stopPropagation = true;
                    originalStopPropagation.call(event);
                },
                ...enumerableProperty,
            },
            stopImmediatePropagation: {
                value: () => {
                    stopImmediatePropagation = true;
                    originalStopImmediatePropagation.call(event);
                },
                ...enumerableProperty,
            },
        });
        // An event handler can either be a function, an object with a handleEvent
        // method or null. This function takes care to call the event handler
        // correctly.
        const invokeEventListener = (listener, options, eventListenerMap) => {
            if (typeof listener === 'function') {
                listener(event);
            }
            else if (typeof listener?.handleEvent === 'function') {
                listener.handleEvent(event);
            }
            if (options.once) {
                eventListenerMap.delete(listener);
            }
        };
        // When an event is finished being dispatched, which can be after the event
        // tree has been traversed or stopPropagation/stopImmediatePropagation has
        // been called. Once that is the case, the currentTarget and eventPhase
        // need to be reset and a value, representing whether the event has not
        // been prevented, needs to be returned.
        const finishDispatch = () => {
            currentTarget = null;
            eventPhase = NONE;
            return !event.defaultPrevented;
        };
        // An event starts with the capture order, where it starts from the top.
        // This is done even if bubbles is set to false, which is the default.
        const captureEventPath = composedPath.slice().reverse();
        // If the event target, which dispatches the event, is either in the light DOM
        // or the event is not composed, the target is always itself. If that is not
        // the case, the target needs to be retargeted: https://dom.spec.whatwg.org/#retarget
        target = !this.__host || !event.composed ? this : null;
        const retarget = (eventTargets) => {
            // eslint-disable-next-line @typescript-eslint/no-this-alias
            tmpTarget = this;
            while (tmpTarget.__host && eventTargets.includes(tmpTarget.__host)) {
                tmpTarget = tmpTarget.__host;
            }
        };
        for (const eventTarget of captureEventPath) {
            if (!target && (!tmpTarget || tmpTarget === eventTarget.__host)) {
                retarget(captureEventPath.slice(captureEventPath.indexOf(eventTarget)));
            }
            currentTarget = eventTarget;
            eventPhase = eventTarget === event.target ? AT_TARGET : CAPTURING_PHASE;
            const captureEventListeners = eventTarget.__captureEventListeners.get(event.type);
            if (captureEventListeners) {
                for (const [listener, options] of captureEventListeners) {
                    invokeEventListener(listener, options, captureEventListeners);
                    if (stopImmediatePropagation) {
                        // Event.stopImmediatePropagation() stops any following invocation
                        // of an event handler even on the same event target.
                        return finishDispatch();
                    }
                }
            }
            if (stopPropagation) {
                // Event.stopPropagation() stops any following invocation
                // of an event handler for any following event targets.
                return finishDispatch();
            }
        }
        const bubbleEventPath = event.bubbles ? composedPath : [this];
        tmpTarget = null;
        for (const eventTarget of bubbleEventPath) {
            if (!target &&
                (!tmpTarget || eventTarget === tmpTarget.__host)) {
                retarget(bubbleEventPath.slice(0, bubbleEventPath.indexOf(eventTarget) + 1));
            }
            currentTarget = eventTarget;
            eventPhase = eventTarget === event.target ? AT_TARGET : BUBBLING_PHASE;
            const captureEventListeners = eventTarget.__eventListeners.get(event.type);
            if (captureEventListeners) {
                for (const [listener, options] of captureEventListeners) {
                    invokeEventListener(listener, options, captureEventListeners);
                    if (stopImmediatePropagation) {
                        // Event.stopImmediatePropagation() stops any following invocation
                        // of an event handler even on the same event target.
                        return finishDispatch();
                    }
                }
            }
            if (stopPropagation) {
                // Event.stopPropagation() stops any following invocation
                // of an event handler for any following event targets.
                return finishDispatch();
            }
        }
        return finishDispatch();
    }
};
const EventTargetShimWithRealType = EventTargetShim;
export { EventTargetShimWithRealType as EventTarget, EventTargetShimWithRealType as EventTargetShim, };
const enumerableProperty = { __proto__: null };
enumerableProperty.enumerable = true;
Object.freeze(enumerableProperty);
// TODO: Remove this when we remove support for vm modules (--experimental-vm-modules).
const EventShim = (_a = class Event {
        constructor(type, options = {}) {
            _Event_cancelable.set(this, false);
            _Event_bubbles.set(this, false);
            _Event_composed.set(this, false);
            _Event_defaultPrevented.set(this, false);
            _Event_timestamp.set(this, Date.now());
            _Event_propagationStopped.set(this, false);
            _Event_type.set(this, void 0);
            _Event_target.set(this, void 0);
            _Event_isBeingDispatched.set(this, void 0);
            this.NONE = NONE;
            this.CAPTURING_PHASE = CAPTURING_PHASE;
            this.AT_TARGET = AT_TARGET;
            this.BUBBLING_PHASE = BUBBLING_PHASE;
            if (arguments.length === 0)
                throw new Error(`The type argument must be specified`);
            if (typeof options !== 'object' || !options) {
                throw new Error(`The "options" argument must be an object`);
            }
            const { bubbles, cancelable, composed } = options;
            __classPrivateFieldSet(this, _Event_cancelable, !!cancelable, "f");
            __classPrivateFieldSet(this, _Event_bubbles, !!bubbles, "f");
            __classPrivateFieldSet(this, _Event_composed, !!composed, "f");
            __classPrivateFieldSet(this, _Event_type, `${type}`, "f");
            __classPrivateFieldSet(this, _Event_target, null, "f");
            __classPrivateFieldSet(this, _Event_isBeingDispatched, false, "f");
        }
        initEvent(_type, _bubbles, _cancelable) {
            throw new Error('Method not implemented.');
        }
        stopImmediatePropagation() {
            this.stopPropagation();
        }
        preventDefault() {
            __classPrivateFieldSet(this, _Event_defaultPrevented, true, "f");
        }
        get target() {
            return __classPrivateFieldGet(this, _Event_target, "f");
        }
        get currentTarget() {
            return __classPrivateFieldGet(this, _Event_target, "f");
        }
        get srcElement() {
            return __classPrivateFieldGet(this, _Event_target, "f");
        }
        get type() {
            return __classPrivateFieldGet(this, _Event_type, "f");
        }
        get cancelable() {
            return __classPrivateFieldGet(this, _Event_cancelable, "f");
        }
        get defaultPrevented() {
            return __classPrivateFieldGet(this, _Event_cancelable, "f") && __classPrivateFieldGet(this, _Event_defaultPrevented, "f");
        }
        get timeStamp() {
            return __classPrivateFieldGet(this, _Event_timestamp, "f");
        }
        composedPath() {
            return __classPrivateFieldGet(this, _Event_isBeingDispatched, "f") ? [__classPrivateFieldGet(this, _Event_target, "f")] : [];
        }
        get returnValue() {
            return !__classPrivateFieldGet(this, _Event_cancelable, "f") || !__classPrivateFieldGet(this, _Event_defaultPrevented, "f");
        }
        get bubbles() {
            return __classPrivateFieldGet(this, _Event_bubbles, "f");
        }
        get composed() {
            return __classPrivateFieldGet(this, _Event_composed, "f");
        }
        get eventPhase() {
            return __classPrivateFieldGet(this, _Event_isBeingDispatched, "f") ? _a.AT_TARGET : _a.NONE;
        }
        get cancelBubble() {
            return __classPrivateFieldGet(this, _Event_propagationStopped, "f");
        }
        set cancelBubble(value) {
            if (value) {
                __classPrivateFieldSet(this, _Event_propagationStopped, true, "f");
            }
        }
        stopPropagation() {
            __classPrivateFieldSet(this, _Event_propagationStopped, true, "f");
        }
        get isTrusted() {
            return false;
        }
    },
    _Event_cancelable = new WeakMap(),
    _Event_bubbles = new WeakMap(),
    _Event_composed = new WeakMap(),
    _Event_defaultPrevented = new WeakMap(),
    _Event_timestamp = new WeakMap(),
    _Event_propagationStopped = new WeakMap(),
    _Event_type = new WeakMap(),
    _Event_target = new WeakMap(),
    _Event_isBeingDispatched = new WeakMap(),
    _a.NONE = NONE,
    _a.CAPTURING_PHASE = CAPTURING_PHASE,
    _a.AT_TARGET = AT_TARGET,
    _a.BUBBLING_PHASE = BUBBLING_PHASE,
    _a);
Object.defineProperties(EventShim.prototype, {
    initEvent: enumerableProperty,
    stopImmediatePropagation: enumerableProperty,
    preventDefault: enumerableProperty,
    target: enumerableProperty,
    currentTarget: enumerableProperty,
    srcElement: enumerableProperty,
    type: enumerableProperty,
    cancelable: enumerableProperty,
    defaultPrevented: enumerableProperty,
    timeStamp: enumerableProperty,
    composedPath: enumerableProperty,
    returnValue: enumerableProperty,
    bubbles: enumerableProperty,
    composed: enumerableProperty,
    eventPhase: enumerableProperty,
    cancelBubble: enumerableProperty,
    stopPropagation: enumerableProperty,
    isTrusted: enumerableProperty,
});
// TODO: Remove this when we remove support for vm modules (--experimental-vm-modules).
const CustomEventShim = (_b = class CustomEvent extends EventShim {
        constructor(type, options = {}) {
            super(type, options);
            _CustomEvent_detail.set(this, void 0);
            __classPrivateFieldSet(this, _CustomEvent_detail, options?.detail ?? null, "f");
        }
        initCustomEvent(_type, _bubbles, _cancelable, _detail) {
            throw new Error('Method not implemented.');
        }
        get detail() {
            return __classPrivateFieldGet(this, _CustomEvent_detail, "f");
        }
    },
    _CustomEvent_detail = new WeakMap(),
    _b);
Object.defineProperties(CustomEventShim.prototype, {
    detail: enumerableProperty,
});
const EventShimWithRealType = EventShim;
const CustomEventShimWithRealType = CustomEventShim;
export { EventShimWithRealType as Event, EventShimWithRealType as EventShim, CustomEventShimWithRealType as CustomEvent, CustomEventShimWithRealType as CustomEventShim, };
//# sourceMappingURL=events.js.map