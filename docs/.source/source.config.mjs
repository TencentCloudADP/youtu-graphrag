// source.config.ts
import {
  defineConfig,
  defineDocs,
  frontmatterSchema,
  metaSchema
} from "fumadocs-mdx/config";
import { z } from "zod";
var docs = defineDocs({
  docs: {
    schema: frontmatterSchema.extend({
      author: z.string().optional(),
      avatar: z.string().optional(),
      github_username: z.string().optional(),
      x_username: z.string().optional(),
      demo_url: z.string().url().optional()
    })
  },
  meta: {
    schema: metaSchema
  }
});
var source_config_default = defineConfig({
  mdxOptions: {
    // MDX options
  }
});
export {
  source_config_default as default,
  docs
};
