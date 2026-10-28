<!-- markdownlint-disable MD013 -->

# Auth0 OAuth/OIDC for the hosted Mathen MCP

This tutorial is for an operator who wants an MCP host such as OpenCode to
authenticate to a hosted Mathen MCP endpoint with Auth0. It describes the
target external OAuth/OIDC arrangement and the checks needed before enabling
it. Mathen remains read-only: an authenticated client can query reviewed
records, but it cannot write cards, promote drafts, or change D1 data.

Replace every value in angle brackets. The examples intentionally contain no
tenant IDs, client secrets, access tokens, or other production credentials.

## Prerequisites

You need:

- an Auth0 tenant with permission to manage tenant settings, APIs/resource
  servers, applications, connections, and grants;
- a stable HTTPS hostname for the Mathen deployment, with separate staging and
  production hostnames if both environments are used;
- a version of OpenCode that supports remote MCP OAuth discovery and the
  `mcp.servers` configuration shape; and
- an operator who can update the deployment's production and staging
  configuration independently.

Use separate Auth0 APIs, applications, and users/connection policies for
staging and production when practical. A staging token must not be accepted by
the production resource.

## 1. Record the Auth0 tenant and issuer

In the Auth0 Dashboard, select the tenant that will issue tokens. Record its
domain, for example:

```text
https://<tenant>.us.auth0.com/
```

The value above, including its canonical trailing slash, is the issuer used in
discovery and token validation. Auth0 custom domains are also possible; use the
same canonical issuer consistently everywhere. Do not substitute the API
identifier for the issuer.

The authorization-server metadata document is normally available at:

```text
https://<tenant>.us.auth0.com/.well-known/openid-configuration
```

Read it back before configuring OpenCode. Confirm that its `issuer`,
`authorization_endpoint`, `token_endpoint`, and `jwks_uri` are present and
match the tenant you selected.

## 2. Create the Mathen API/resource server

In **Applications → APIs**, create an API representing the protected MCP
resource. Use an absolute URI as its identifier. It should identify the same
resource that the MCP client is calling, not a management API or a human login
page. For example:

```text
Name:       <Mathen MCP production>
Identifier: https://<mathen-production-host>/api/mcp
Signing algorithm: RS256
```

For staging, use a different identifier such as
`https://<mathen-staging-host>/api/mcp`. The identifier is the OAuth audience
(`aud`) and, with the MCP resource parameter flow, the value sent as
`resource`. It must be an absolute URI and must match the protected resource
metadata exactly.

Add the narrow API permission:

```text
Scope: mathen:read
Description: Read reviewed Mathen records through MCP
```

Use **RS256** rather than a symmetric signing algorithm. The Worker can then
validate Auth0 JWTs against the tenant's published JWKS without sharing a
signing secret with Mathen. Configure the API to issue an access token for this
resource server and grant only `mathen:read` to the clients and users that
need it. A requested scope is not proof that it was granted; verify the
resulting token's `aud` and `scope`/permissions claims during testing.

## 3. Enable the MCP-compatible Auth0 settings

In the Auth0 Dashboard, open the tenant's **Advanced** settings and enable:

1. **Resource Parameter Compatibility Profile**. MCP clients use the
   standards-based RFC 8707 `resource` parameter. This setting lets Auth0 use
   that resource to bind the token to the API. The API identifier should be an
   absolute URI.
2. **Include Issuer in Authorization Responses**. This adds the `iss`
   authorization-response parameter so a client can detect an authorization
   server mix-up and verify that the response came from the discovered issuer.

Do not silently replace `resource` with an unrelated `audience` value to make a
login appear to work. If both are sent, Auth0's compatibility behavior gives
the explicit API audience precedence; keep them equal when both are required
by a client or compatibility path.

## 4. Configure the login connection

Choose the connection that users may use to authorize Mathen access (for
example, an Auth0 database connection, an enterprise OIDC connection, or a
social connection). In the Auth0 application/client registration used by the
MCP host:

1. enable that connection for the application;
2. confirm the connection's login and consent behavior is suitable for a
   third-party MCP client;
3. allow the application to request the `mathen:read` API permission; and
4. if the tenant requires domain-level connections for third-party MCP
   clients, promote the selected connection according to Auth0's current
   tenant policy.

Keep the login policy least-privilege. Requiring MFA, organization membership,
or an explicit consent screen is an Auth0 policy decision; document it for the
staging and production tenants rather than assuming the two tenants behave the
same way.

## 5. Publish protected-resource metadata

The MCP resource must publish OAuth protected-resource metadata at a public
HTTPS URL. The hosted Mathen API exposes the primary metadata URL below, plus
an optional `/mcp` compatibility URL:

```text
https://<mathen-production-host>/api/.well-known/oauth-protected-resource
https://<mathen-production-host>/api/.well-known/oauth-protected-resource/mcp
```

Use the primary URL advertised by the deployed MCP 401 challenge. The
document should contain values like these:

```json
{
  "resource": "https://<mathen-production-host>/api/mcp",
  "authorization_servers": [
    "https://<tenant>.us.auth0.com/"
  ],
  "scopes_supported": ["mathen:read"],
  "bearer_methods_supported": ["header"]
}
```

Do not put a client secret, access token, or registration credential in this
document. It is public discovery metadata. The Auth0 tenant owns the
authorization-server metadata at its own `.well-known/openid-configuration`
URL; Mathen owns the protected-resource metadata.

When unauthenticated access is attempted, the MCP endpoint should return
`401 Unauthorized` with a `WWW-Authenticate` Bearer challenge whose
`resource_metadata` parameter points to the protected-resource metadata URL.
The client then discovers the Auth0 issuer, authorization endpoint, token
endpoint, supported scopes, and registration capabilities before starting
login.

## 6. Choose client registration: pre-registration, CIMD, or DCR

MCP hosts can be deployed by many users, so the authorization server needs a
way to identify the OAuth client. Choose one strategy deliberately:

### Client ID Metadata Document (CIMD)

If the Auth0 tenant and OpenCode version support CIMD, host a client metadata
JSON document at an HTTPS URL controlled by the client deployment. The URL is
the client ID. A public client document resembles:

```json
{
  "client_id": "https://<client-host>/<client-metadata-path>.json",
  "client_name": "<OpenCode Mathen MCP client>",
  "application_type": "native",
  "grant_types": ["authorization_code"],
  "response_types": ["code"],
  "redirect_uris": ["http://127.0.0.1:<callback-port>/callback"],
  "token_endpoint_auth_method": "none"
}
```

The document must be served over HTTPS, except for the loopback redirect used
by a native client. Keep its redirect URI exact. CIMD is not a place to embed a
client secret. Auth0's current CIMD controls distinguish importing a document
manually from allowing dynamic CIMD registration; enable only the mode your
tenant has reviewed. Strict third-party client policies and legacy Auth0 Rules
can affect CIMD login, so test the chosen connection with the actual client.

### Dynamic Client Registration (DCR)

If the tenant advertises and permits DCR, OpenCode can register its public
client metadata at the authorization server's registration endpoint. Treat an
open registration endpoint as a security and lifecycle decision: restrict
allowed clients or registrations where the tenant supports that control, and
monitor registrations. Do not assume DCR is enabled merely because the
authorization server supports OAuth discovery.

### Pre-registered public client

For a controlled deployment, register an Auth0 application in advance and give
OpenCode only its client ID. Use a public/native application with no client
secret and an exact loopback redirect URI. This is often the simplest fallback
when CIMD or DCR is unavailable. If an administrator gives you a client
secret, do not put it in a repository, prompt, chat, URL, or shared OpenCode
configuration; use a separate confidential-client design instead.

### PKCE

Use the authorization-code flow with **PKCE S256**. OpenCode should generate a
fresh `state` and PKCE verifier/challenge for every login, validate `state` and
the authorization-response issuer, and exchange the code at Auth0's token
endpoint. Never use the implicit flow for this integration. Do not disable PKCE
to work around a redirect or registration error; correct the client metadata
and redirect URI.

## 7. Configure OpenCode

Add the hosted MCP server to the OpenCode configuration file (usually
`~/.config/opencode/opencode.jsonc`, or the equivalent project configuration).
Remote servers use OAuth when `oauth` is omitted or configured as an OAuth
object. The `mcp.servers` nesting is important:

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "servers": {
      "mathen": {
        "type": "remote",
        "url": "https://<mathen-production-host>/api/mcp",
        "oauth": {
          "scope": "mathen:read"
          // If discovery cannot find Auth0, provide the issuer metadata URL:
          // "auth_server_metadata_url":
          //   "https://<tenant>.us.auth0.com/.well-known/openid-configuration"
        }
      }
    }
  }
}
```

For a pre-registered client, add its client ID through an environment
interpolation rather than writing it inline if the local policy requires that:

```jsonc
"oauth": {
  "client_id": "{env:MATHEN_MCP_CLIENT_ID}",
  "scope": "mathen:read",
  "callback_port": 19876,
  "redirect_uri": "http://127.0.0.1:19876/callback"
}
```

Do not set `oauth: false` for the Auth0 flow. That setting disables automatic
OAuth and is for the legacy Bearer-token path described below. Do not add an
`Authorization` header containing a copied access token to this file.

Start OpenCode, open the MCP management view, and run:

```text
/mcps
```

Select `mathen`, choose **Connect** or **Login**, and complete the Auth0
browser flow. Approve only the requested `mathen:read` permission. OpenCode
should cache the resulting OAuth credentials in its own credential store, not
in the repository or conversation. If the client reports that the server
needs authentication, repeat `/mcps` and select the server; do not paste an
authorization URL or token into chat. A CLI `opencode mcp auth <name>` command
may exist in your version, but the user-facing `/mcps` flow is the preferred
interactive path.

## 8. Configure deployment variables safely

For an OAuth-capable Worker, configure these as **production Variables**, not
secrets:

| Variable | Example placeholder | Purpose |
| --- | --- | --- |
| `AUTH0_ISSUER` | `https://<tenant>.us.auth0.com/` | Exact issuer used for discovery/JWKS and `iss` validation |
| `AUTH0_AUDIENCE` | `https://<mathen-production-host>/api/mcp` | Exact Auth0 API identifier and expected token audience |
| `AUTH0_REQUIRED_SCOPE` | `mathen:read` | Scope required for the read-only MCP resource |

Set separate values for staging. These values are not credentials, but they
must still be reviewed because a wrong issuer or audience can accept the wrong
resource or reject every valid token.

Keep `API_ACCESS_TOKEN` as a **Secret** for the retained legacy Bearer path.
The deployment workflow currently writes that secret when it is present. Never
move it to a public Worker variable. Rotate or revoke it in the Worker when it
is exposed.

The checked-in `apps/api/wrangler.jsonc` defines the optional Auth0 variables
above, and the deploy workflow forwards them from GitHub production Variables.
No real Auth0 tenant values have been configured, deployed, or live-verified.
Treat this tutorial as the operator configuration contract for an OAuth-enabled
deployment and do not claim OAuth is active until those deployment and live
verification checks are complete.

At no point should a secret or access token appear in a repository, issue,
chat, command history, URL query string, browser bundle, card, or log. Use
environment/secret stores and redact request/CI output.

## 9. Verify staging, then production

Run the following checks against staging first, using the staging host and
issuer. Repeat them against production only after staging succeeds.

1. Read the protected-resource metadata without credentials and confirm its
   `resource`, `authorization_servers`, and `scopes_supported` values.
2. Read Auth0's authorization-server metadata and confirm the issuer, JWKS,
   authorization, token, and (if used) registration endpoints.
3. Request the MCP endpoint without credentials. Confirm `401` and a
   `WWW-Authenticate` challenge with the correct `resource_metadata` URL.
4. In OpenCode, use `/mcps` to complete login. Confirm the browser redirect
   returns to the exact loopback URI and that the client requested
   `mathen:read`, not a broad or unrelated API scope.
5. Call MCP `initialize`, `tools/list`, and one harmless read-only tool. Confirm
   success and verify in the Worker logs that no token, authorization code, or
   PKCE verifier was logged.
6. Test rejection: use an expired token, a token with the wrong `aud`, the
   wrong issuer, and a token without `mathen:read`. Each must be rejected.
7. Confirm a token issued for staging is rejected by production, and that
   production still serves only reviewed canonical records.
8. Record status codes, deployment version, request IDs, issuer/audience
   configuration, and tool result shape. Record no credentials.

For a controlled command-line check, keep a short-lived token only in the
process environment and never put it in the URL or shell transcript:

```bash
export MATHEN_OAUTH_ACCESS_TOKEN='[short-lived token supplied by your secure test process]'
curl --fail-with-body \
  -H "Authorization: Bearer ${MATHEN_OAUTH_ACCESS_TOKEN}" \
  -H 'Content-Type: application/json' \
  'https://<mathen-staging-host>/api/mcp'
unset MATHEN_OAUTH_ACCESS_TOKEN
```

Use the MCP JSON-RPC request body appropriate for your client when doing a
protocol check. Do not copy the placeholder command into a production log with
a real token in the environment or process arguments.

## Legacy Bearer fallback

Until OAuth validation is explicitly enabled and verified, the hosted Mathen
MCP endpoint uses the retained exact-match service credential:

```jsonc
{
  "mcp": {
    "servers": {
      "mathen-legacy": {
        "type": "remote",
        "url": "https://<mathen-host>/api/mcp",
        "oauth": false,
        "headers": {
          "Authorization": "Bearer {env:API_ACCESS_TOKEN}"
        }
      }
    }
  }
}
```

Export `API_ACCESS_TOKEN` only in the environment of the OpenCode process.
This is a service-token fallback, not a user login, and it does not prove that
Auth0 OAuth is configured. Do not configure both an OAuth flow and a copied
Bearer header for the same server name; choose one deliberately so a failed
OAuth login cannot be mistaken for a successful legacy login.

## Troubleshooting

| Symptom | Likely cause and fix |
| --- | --- |
| OpenCode reports no authorization server | The protected-resource metadata is missing, not public, or does not list the Auth0 issuer. Check the 401 `resource_metadata` URL and JSON. |
| Auth0 rejects `resource` or the token has the wrong audience | Enable Resource Parameter Compatibility Profile and make the API identifier, `resource`, metadata `resource`, and expected `aud` the same absolute URI. |
| `iss` is missing or issuer validation fails | Enable Include Issuer in Authorization Responses and use one canonical issuer, including trailing-slash behavior, in Auth0, metadata, and Worker Variables. |
| Login succeeds but MCP returns 403 | The user/client was not granted `mathen:read`, the scope was not included in the access token, or the Worker requires a different audience. Check grants and token claims without logging the token. |
| Redirect or PKCE error | Use authorization code + PKCE S256, register the exact loopback redirect, use a fresh browser login, and do not add a client secret to a public client. |
| CIMD registration fails | Confirm the metadata URL is HTTPS, `client_id` exactly equals that URL, redirect URIs are exact, and the tenant supports the selected manual/dynamic CIMD mode. Check for legacy Rules that are incompatible with strict third-party clients. |
| DCR is unavailable | Use a manually imported CIMD client or a pre-registered public Auth0 application. DCR support is tenant- and policy-dependent. |
| `/mcps` keeps asking for login | Remove `oauth: false` and any stale legacy `Authorization` header, restart OpenCode, and reconnect the server. Check that the server URL is unchanged. |
| Legacy setup returns 401 | `API_ACCESS_TOKEN` is absent, expired/revoked, or does not exactly match the Worker Secret. Keep it out of URLs and rotate it if exposed. |
| Browser request is rejected by CORS | The request `Origin` must exactly match `MCP_ALLOWED_ORIGINS`. This is separate from OAuth token validation. A non-browser OpenCode request normally has no browser origin. |

## Current limitations

This tutorial must not be read as a deployment claim. In the current checked-in
Mathen implementation:

- the hosted `/api/mcp` authorization path performs exact `Bearer
  API_ACCESS_TOKEN` matching and also contains optional Auth0 JWT/JWKS, issuer,
  audience, and scope validation when the Auth0 variables are configured;
- the Worker code now publishes the protected-resource metadata routes at
  `/api/.well-known/oauth-protected-resource` and the optional
  `/api/.well-known/oauth-protected-resource/mcp`, and emits the OAuth-specific
  `WWW-Authenticate` challenge when Auth0 validation is configured;
- `AUTH0_ISSUER`, `AUTH0_AUDIENCE`, `AUTH0_JWKS_URI`, and
  `AUTH0_REQUIRED_SCOPE` are declared and forwarded by the checked-in
  deployment configuration, but no real Auth0 tenant variables have been
  configured, deployed, or live-verified;
- OpenCode OAuth support, Auth0 tenant capabilities, CIMD/DCR availability,
  redirect handling, and credential storage vary by client and version; verify
  the versions used by the operator;
- Auth0 login does not turn Mathen into a write API. The MCP surface remains
  stateless, reviewed-only, and read-only; drafts and local analysis artifacts
  remain outside production MCP output; and
- no OAuth success, staging result, production deployment, or token rotation
  should be claimed from source configuration alone. Perform the staging and
  production read-back checks above and retain only non-secret evidence.

Until those deployment and live-verification checks are complete, the legacy
`API_ACCESS_TOKEN` path remains the currently verified production path. Treat
Auth0 configuration as preparation for a future OAuth-enabled deployment.

## References

- [Mathen MCP server](mcp.md) — current hosted and stdio MCP boundary
- [Hosting and integration boundaries](hosting.md) — Worker variables, secrets,
  deployment workflow, CORS, and verification responsibilities
- [Mathen CLI configuration](configuration.md) — hosted MCP URL/token settings
- [Auth0: Authorization for your MCP server](https://auth0.com/ai/docs/mcp/get-started/authorization-for-your-mcp-server)
- [Auth0: Resource Parameter Compatibility Profile](https://auth0.com/ai/docs/mcp/guides/resource-param-compatibility-profile)
- [Auth0: Client ID Metadata Document registration](https://auth0.com/docs/get-started/auth0-overview/create-applications/cimd-overview)
- [OpenCode: MCP servers](https://opencode.ai/docs/mcp-servers/)
