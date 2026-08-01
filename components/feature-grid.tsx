"use client"

import { TerminalCard } from "@/components/bento/terminal-card"
import { DitherCard } from "@/components/bento/dither-card"
import { MetricsCard } from "@/components/bento/metrics-card"
import { StatusCard } from "@/components/bento/status-card"
import { motion } from "framer-motion"

const ease = [0.22, 1, 0.36, 1] as const

const cardVariants = {
  hidden: { opacity: 0, y: 30 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.1, duration: 0.6, ease },
  }),
}

export function FeatureGrid() {
  return (
    <section className="w-full px-6 py-20 lg:px-12">
      {/* Section label */}
      <motion.div
        initial={{ opacity: 0, x: -20 }}
        whileInView={{ opacity: 1, x: 0 }}
        viewport={{ once: true, margin: "-80px" }}
        transition={{ duration: 0.5, ease }}
        className="flex items-center gap-4 mb-8"
      >
        <span className="text-[10px] tracking-[0.2em] uppercase text-muted-foreground">
          {"// SECTION: CORE_REQUIREMENTS"}
        </span>
        <div className="flex-1 border-t border-border" />
        <span className="text-[10px] tracking-[0.2em] uppercase text-muted-foreground">01</span>
      </motion.div>

      {/* 2x2 Bento Grid */}
      <motion.div
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true, margin: "-60px" }}
        className="grid grid-cols-1 md:grid-cols-2 border-2 border-foreground"
      >
        {/* Card 1 */}
        <motion.div
          custom={0}
          variants={cardVariants}
          className="border-b-2 md:border-b-0 md:border-r-2 border-foreground min-h-[280px] p-8 flex flex-col justify-center"
        >
          <span className="text-[10px] tracking-[0.2em] uppercase text-muted-foreground mb-4 font-mono">REQ_01</span>
          <p className="text-sm lg:text-base font-mono text-foreground leading-relaxed">Spend limits enforced at the wallet or contract layer — not inside the agent's own logic.</p>
        </motion.div>

        {/* Card 2 */}
        <motion.div
          custom={1}
          variants={cardVariants}
          className="border-b-2 md:border-b-0 border-foreground min-h-[280px] p-8 flex flex-col justify-center"
        >
          <span className="text-[10px] tracking-[0.2em] uppercase text-[#ea580c] mb-4 font-mono">REQ_02</span>
          <p className="text-sm lg:text-base font-mono text-foreground leading-relaxed">Allowlisted counterparties, so the agent can only transact with pre-approved parties.</p>
        </motion.div>

        {/* Card 3 */}
        <motion.div
          custom={2}
          variants={cardVariants}
          className="border-t-2 md:border-r-2 border-foreground min-h-[280px] p-8 flex flex-col justify-center"
        >
          <span className="text-[10px] tracking-[0.2em] uppercase text-muted-foreground mb-4 font-mono">REQ_03</span>
          <p className="text-sm lg:text-base font-mono text-foreground leading-relaxed">An owner-controlled mechanism to freeze the agent mid-execution, at any point.</p>
        </motion.div>

        {/* Card 4 */}
        <motion.div
          custom={3}
          variants={cardVariants}
          className="border-t-2 border-foreground min-h-[280px] p-8 flex flex-col justify-center"
        >
          <span className="text-[10px] tracking-[0.2em] uppercase text-muted-foreground mb-4 font-mono">REQ_04</span>
          <p className="text-sm lg:text-base font-mono text-foreground leading-relaxed">A demo showing the agent running unsupervised, attempting to exceed its policy, and being blocked.</p>
        </motion.div>
      </motion.div>
    </section>
  )
}
