import { checkoutHandler } from '../_shared/billing.mjs';
Deno.serve((request: Request) => checkoutHandler(request, Deno.env.toObject()));
