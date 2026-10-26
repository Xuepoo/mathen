import { expect, test } from "bun:test";
import { readFileSync } from "node:fs";
import {
  createRetrievalSearch,
  mountRetrieval,
  renderRetrievalState,
  type RetrievalState,
} from "./retrieval";

function fixture() {
  return {
    schema_version: "1.0",
    query: { q_digest: "sha256:q", filters: {} },
    index: {
      status: "ready",
      index_id: "canonical-cards-d1-lexical-v1",
      corpus: "canonical_cards",
      representation_version: "canonical-record-v1",
      method: "bounded_lexical_baseline",
      warnings: ["Uncalibrated ranking"],
    },
    results: [
      {
        rank: 1,
        score: 0.75,
        score_kind: "lexical_overlap",
        document: {
          id: "system:alpha:feature:embedded",
          system_id: "alpha",
          record_kind: "feature",
          name: "Embedded <script>",
          description: "Runs in process.",
          claim_type: "hypothesis",
          claim_status: "under-review",
          version_context: "1.0",
          validity_scope: { deployment_origins: ["local"], conditions: ["one process"] },
          evidence_ids: ["architecture"],
        },
        evidence: [
          {
            id: "architecture",
            kind: "doc",
            title: "Architecture",
            uri: "https://example.test/doc",
          },
        ],
        provenance: {
          source_ref: "data/systems/alpha.json#features/embedded",
          source_digest: "sha256:source",
          retrieval_method: "bounded_lexical_baseline",
        },
      },
    ],
    warnings: ["stale_source_ref"],
  };
}

test("discovery is discoverable without changing graph controls or mobile layout", () => {
  const main = readFileSync(new URL("./main.ts", import.meta.url), "utf8");
  expect(main).toContain("Browse systems & discover");
  expect(main).toContain('id="retrieval"');
  expect(main).toContain("mountRetrieval");
  expect(main).not.toContain(
    "Semantic/vector retrieval is planned rather than implemented in this browser",
  );
});

test("search is same-origin, bounded, trimmed and loading precedes deterministic results", async () => {
  const states: RetrievalState[] = [];
  let url = "";
  let resolve!: (response: Response) => void;
  const search = createRetrievalSearch(
    (state) => states.push(state),
    async (input) => {
      url = input;
      return new Promise<Response>((done) => {
        resolve = done;
      });
    },
  );
  const pending = search.search("  state & queues  ");
  expect(states.at(-1)?.status).toBe("loading");
  expect(url).toBe("/api/retrieval?q=state+%26+queues&limit=10");
  resolve(Response.json({ data: fixture() }));
  await pending;
  const html = renderRetrievalState(states.at(-1)!);
  for (const text of [
    "lexical_overlap",
    "bounded_lexical_baseline",
    "hypothesis",
    "under-review",
    "architecture",
    "https://example.test/doc",
    "data/systems/alpha.json#features/embedded",
    "sha256:source",
    "local",
    "one process",
    "1.0",
    "stale_source_ref",
    "uncalibrated",
    "semantic proof",
    "compatibility",
    "relation",
    "causality",
    "originality",
    'data-retrieval-card="alpha"',
  ])
    expect(html).toContain(text);
  expect(html).toContain("Embedded &lt;script&gt;");
  expect(html).not.toContain("<script>");
  expect(renderRetrievalState(states.at(-1)!)).toBe(html);
});

test("no matches, empty corpus, unavailable and invalid responses remain distinct", async () => {
  for (const status of ["ready", "empty"]) {
    let state: RetrievalState = { status: "idle" };
    const value = { ...fixture(), index: { ...fixture().index, status }, results: [] };
    await createRetrievalSearch(
      (next) => {
        state = next;
      },
      async () => Response.json({ data: value }),
    ).search("absent");
    expect(renderRetrievalState(state)).toContain(
      status === "ready" ? "No matching reviewed records" : "No eligible reviewed records",
    );
    expect(renderRetrievalState(state)).toContain(
      "does not establish that no relevant architecture exists",
    );
  }
  for (const [response, expected] of [
    [new Response("provider-secret", { status: 503 }), "unavailable"],
    [new Response("token-secret", { status: 403 }), "error"],
    [Response.json({ data: {} }), "error"],
  ] as const) {
    let state: RetrievalState = { status: "idle" };
    await createRetrievalSearch(
      (next) => {
        state = next;
      },
      async () => response,
    ).search("private-query");
    expect(String(state.status)).toBe(expected);
    expect(renderRetrievalState(state)).not.toMatch(/provider-secret|token-secret|private-query/);
    expect(renderRetrievalState(state)).toContain("Browse systems");
  }
});

test("stale searches cannot replace a newer request and invalid input never fetches", async () => {
  let state: RetrievalState = { status: "idle" };
  const replies: ((response: Response) => void)[] = [];
  const search = createRetrievalSearch(
    (next) => {
      state = next;
    },
    async () => new Promise<Response>((done) => replies.push(done)),
  );
  await search.search(" ");
  expect(String(state.status)).toBe("error");
  expect(replies).toHaveLength(0);
  await search.search("x".repeat(1001));
  expect(replies).toHaveLength(0);
  const first = search.search("first");
  const second = search.search("second");
  replies[1](Response.json({ data: { ...fixture(), results: [] } }));
  await second;
  replies[0](Response.json({ data: fixture() }));
  await first;
  expect(renderRetrievalState(state)).toContain("No matching reviewed records");
});

test("unsafe evidence links are inert and missing metadata is not upgraded", async () => {
  const value = fixture();
  value.results[0].evidence[0].uri = "javascript:alert(1)";
  delete (value.results[0].document as { claim_status?: string }).claim_status;
  let state: RetrievalState = { status: "idle" };
  await createRetrievalSearch(
    (next) => {
      state = next;
    },
    async () => Response.json({ data: value }),
  ).search("state");
  const html = renderRetrievalState(state);
  expect(html).not.toContain('href="javascript:');
  expect(html).toContain("Not supplied");
  expect(html).not.toContain("accepted");
});

test("network failures and timeouts are bounded, sanitized and retryable", async () => {
  let state: RetrievalState = { status: "idle" };
  let calls = 0;
  const search = createRetrievalSearch(
    (next) => {
      state = next;
    },
    async (_input, init) => {
      calls++;
      if (calls === 1) throw new Error("private-query service-secret");
      if (calls === 2)
        return new Promise<Response>((_resolve, reject) => {
          init?.signal?.addEventListener("abort", () =>
            reject(new DOMException("secret", "AbortError")),
          );
        });
      return Response.json({ data: fixture() });
    },
    5,
  );
  await search.search("private-query");
  expect(String(state.status)).toBe("error");
  expect(renderRetrievalState(state)).not.toMatch(/private-query|service-secret/);
  await search.search("private-query");
  expect(String(state.status)).toBe("unavailable");
  await search.search("embedded");
  expect(String(state.status)).toBe("ready");
});

test("mount wires submit, busy state, result-card navigation and explicit browsing actions", async () => {
  const submit = { disabled: false };
  const input = { value: "embedded" };
  const form = Object.assign(new EventTarget(), { querySelector: () => submit });
  const attributes = new Map<string, string>();
  const output = Object.assign(new EventTarget(), {
    innerHTML: "",
    setAttribute: (key: string, value: string) => attributes.set(key, value),
  });
  const host = {
    innerHTML: "",
    querySelector: (selector: string) =>
      selector === "form" ? form : selector === "input" ? input : output,
  };
  let opened = "";
  let browsed = false;
  const originalFetch = globalThis.fetch;
  let finish!: (response: Response) => void;
  let fetched!: () => void;
  const requested = new Promise<void>((resolve) => {
    fetched = resolve;
  });
  globalThis.fetch = Object.assign(
    async () => {
      fetched();
      return new Promise<Response>((resolve) => {
        finish = resolve;
      });
    },
    { preconnect: originalFetch.preconnect },
  );
  try {
    mountRetrieval(
      host as unknown as HTMLElement,
      (id) => {
        opened = id;
      },
      () => {
        browsed = true;
      },
    );
    expect(host.innerHTML).toContain('type="submit"');
    const event = new Event("submit", { cancelable: true });
    form.dispatchEvent(event);
    await requested;
    expect(event.defaultPrevented).toBe(true);
    expect(submit.disabled).toBe(true);
    expect(attributes.get("aria-busy")).toBe("true");
    finish(Response.json({ data: fixture() }));
    await new Promise<void>((resolve) => queueMicrotask(() => queueMicrotask(resolve)));
    expect(output.innerHTML).toContain('data-retrieval-card="alpha"');
    expect(submit.disabled).toBe(false);
    expect(attributes.get("aria-busy")).toBe("false");
    for (const button of [
      { dataset: { retrievalCard: "alpha" }, hasAttribute: () => false },
      { dataset: {}, hasAttribute: () => true },
    ]) {
      const click = new Event("click");
      Object.defineProperty(click, "target", { value: { closest: () => button } });
      output.dispatchEvent(click);
    }
    expect(opened).toBe("alpha");
    expect(browsed).toBe(true);
  } finally {
    globalThis.fetch = originalFetch;
  }
});
