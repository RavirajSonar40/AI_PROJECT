import { Component } from '@angular/core';
import { ChatPanelComponent } from '../features/chat-panel/chat-panel.component';
import { SystemStatusComponent } from '../features/system-status/system-status.component';

@Component({
  standalone: true,
  imports: [ChatPanelComponent, SystemStatusComponent],
  template: `
    <div class="page-grid">
      <app-chat-panel />
      <aside class="right-column">
        <app-system-status />
        <section class="architecture panel-surface">
          <span class="eyebrow">CURRENT FLOW</span>
          <div class="flow">Angular</div><span>↓</span>
          <div class="flow">FastAPI</div><span>↓</span>
          <div class="flow">LangGraph</div><span>↓</span>
          <div class="flow">RAG · Tools · LLM</div>
        </section>
      </aside>
    </div>
  `,
})
export class AgentPageComponent {}
