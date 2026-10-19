import { webhookHandler } from '../_shared/billing.mjs';
Deno.serve((request: Request) => webhookHandler(request, Deno.env.toObject()));
