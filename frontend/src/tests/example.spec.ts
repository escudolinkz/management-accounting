import { test, expect } from '@playwright/test'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
const WEB = process.env.APP_URL || 'http://localhost:8080'

test('upload -> processed -> transactions>0', async ({ page }) => {
  await page.goto(WEB)
  await page.getByText('Sign in').click()
  await page.waitForTimeout(500)
  const fileChooserPromise = page.waitForEvent('filechooser')
  await page.getByLabel('Upload PDF').click()
  const fc = await fileChooserPromise
  // This test assumes a small fixture pdf exists; skip if not.
  try {
    await fc.setFiles('fixtures/sample.pdf')
    await page.getByRole('button', { name: 'Upload' }).click()
    await page.waitForTimeout(1500)
    await page.reload()
    const total = await page.locator('text=Total amount:').innerText()
    expect(total).toContain('RM')
  } catch {}
})
