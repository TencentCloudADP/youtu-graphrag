import { EventTargetShimMeta } from './lib/events.js';
export { ariaMixinAttributes, ElementInternals, HYDRATE_INTERNALS_ATTR_PREFIX, } from './lib/element-internals.js';
export { CustomEvent, Event, EventTarget } from './lib/events.js';
export type HTMLElementWithEventMeta = HTMLElement & EventTargetShimMeta;
declare const ElementShimWithRealType: typeof Element;
export { ElementShimWithRealType as Element };
declare const HTMLElementShimWithRealType: typeof HTMLElement;
export { HTMLElementShimWithRealType as HTMLElement };
declare const CustomElementRegistryShimWithRealType: typeof CustomElementRegistry;
export { CustomElementRegistryShimWithRealType as CustomElementRegistry };
export declare const customElements: CustomElementRegistry;
//# sourceMappingURL=index.d.ts.map