import type { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { type Backend, RetrievalUnavailableError } from "./backend.js";
import { RETRIEVAL_CLAIMS, RETRIEVAL_STATUSES, RETRIEVAL_WARNING } from "./retrieval-contract.js";

/** The legacy tool name is wire-compatible; it does not imply semantic similarity. */
export function registerRetrievalTool(
  server: McpServer,
  backend: Pick<Backend, "searchRetrieval">,
) {
  server.registerTool(
    "search_semantic",
    {
      description: `Discover reviewed canonical records using a bounded lexical baseline, not embeddings or semantic/vector similarity. ${RETRIEVAL_WARNING} Filesystem mode is unavailable without a verified local index; use API mode.`,
      inputSchema: z
        .object({
          q: z.string().trim().min(1).max(1000),
          limit: z.number().int().min(1).max(50).optional(),
          record_kind: z.string().min(1).max(200).optional(),
          system_id: z.string().min(1).max(200).optional(),
          feature_id: z.string().min(1).max(200).optional(),
          category: z.string().min(1).max(200).optional(),
          claim_type: z.enum(RETRIEVAL_CLAIMS).optional(),
          claim_status: z.enum(RETRIEVAL_STATUSES).optional(),
          version_context: z.string().min(1).max(200).optional(),
          deployment_origin: z
            .string()
            .regex(/^[A-Za-z0-9][A-Za-z0-9._:-]{0,99}$/)
            .optional(),
        })
        .strict(),
      annotations: {
        readOnlyHint: true,
        destructiveHint: false,
        idempotentHint: true,
        openWorldHint: false,
      },
    },
    async (args) => {
      try {
        return {
          content: [
            {
              type: "text" as const,
              text: JSON.stringify(await backend.searchRetrieval(args), null, 2),
            },
          ],
        };
      } catch (error) {
        const unavailable = error instanceof RetrievalUnavailableError;
        return {
          isError: true,
          content: [
            {
              type: "text" as const,
              text: JSON.stringify({
                error: unavailable
                  ? error.message
                  : "Retrieval request failed; check arguments and API access or retry later.",
                code: unavailable ? "semantic_index_unavailable" : "retrieval_request_failed",
              }),
            },
          ],
        };
      }
    },
  );
}
