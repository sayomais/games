"use client"

import { useEffect } from "react"
import Prism from "prismjs"
import "prismjs/themes/prism-tomorrow.css"

export default function CodeDisplay() {
  useEffect(() => {
    Prism.highlightAll()
  }, [])

  const code = `const VDX = new Object() || {};
VDX.configuration = {
    gates: [
        {
            gate_id: "stripe_auth1",
            gate_name: "Stripe Auth",
            is_active: true,
            extra_fields: null
        },
        {
            gate_id: "stripe_based1", 
            gate_name: "SK based 1$",
            is_active: false,
            extra_fields: [
                {
                    field_id: "stripe_sk_key1",
                    field_name: "SK Key",
                    field_type: "text",
                    field_placeholder: "sk_live_xxxxxx"
                }
            ]
        },
        {
            gate_id: "stripe_invoice",
            gate_name: "Invoice Hitter",
            is_active: false,
            extra_fields: [
                {
                    field_id: "stripe_invoice_url",
                    field_name: "URL",
                    field_type: "text",
                    field_placeholder: "https://invoice.stripe.com/xxxxx"
                }
            ]
        }
    ]
}`

  return (
    <div className="min-h-screen bg-[#1e1e1e] p-6 font-mono">
      <pre className="rounded-lg">
        <code className="language-javascript">{code}</code>
      </pre>
    </div>
  )
}

