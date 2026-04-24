/**
 * Normalize a FastAPI/Pydantic error response into a plain string.
 *
 * FastAPI can return `detail` as:
 *   - string:  "Not found"
 *   - array:   [{type, loc, msg, input, ctx}, ...]  (Pydantic v2 validation errors)
 *   - object:  {message: "..."}  (some custom handlers)
 *
 * Passing any of these directly to React (as a child or to toast.error) throws
 * "Objects are not valid as a React child".
 */
export function extractErrorMessage(error: unknown, fallback: string): string {
  if (!error || typeof error !== 'object') return fallback

  const err = error as Record<string, any>
  const detail = err?.response?.data?.detail ?? err?.data?.detail

  if (detail != null) {
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) {
      const msgs = detail.map((e: any) => (typeof e?.msg === 'string' ? e.msg : String(e)))
      return msgs.join('; ')
    }
    if (typeof detail === 'object' && typeof detail.message === 'string') {
      return detail.message
    }
  }

  // Fallback chain: axios message, generic message, provided fallback
  const msg = err?.message ?? err?.response?.data?.message
  return typeof msg === 'string' && msg ? msg : fallback
}
