/**
 * Stub: returns true if key is longer than 20 characters, false otherwise.
 * Replace with real cryptographic validation later.
 */
export function validateLicenseKey(key: string): Promise<boolean> {
  return Promise.resolve(key.length > 20);
}
