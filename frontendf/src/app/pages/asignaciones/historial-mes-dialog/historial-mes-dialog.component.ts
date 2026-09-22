import { CommonModule } from '@angular/common';
import { Component, Inject, OnInit } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { AsignacionService } from '../../../services/asignacion.service';

interface HistItem {
  hora: string; usuario: string; accion: string; accion_key: string;
  cliente: string; puesto: string; antes: string; despues: string; persona: string;
}
interface HistDia { fecha: string; items: HistItem[]; }

@Component({
  selector: 'app-historial-mes-dialog',
  standalone: true,
  imports: [CommonModule, MatDialogModule, MatButtonModule, MatIconModule],
  template: `
    <h2 mat-dialog-title>Historial del mes · Movimientos por día</h2>
    <mat-dialog-content class="hist-content">
      <div class="hist-sub">
        {{ nombreMes }} {{ data.anio }}
        <span *ngIf="!cargando"> · {{ total }} movimiento(s)</span>
      </div>

      <div *ngIf="cargando" class="hist-msg">Cargando…</div>
      <div *ngIf="!cargando && dias.length === 0" class="hist-msg">
        No hay movimientos registrados en este mes.
      </div>

      <div *ngFor="let d of dias" class="hist-dia">
        <div class="hist-dia-cab">{{ formatoDia(d.fecha) }}
          <span class="hist-dia-count">{{ d.items.length }}</span>
        </div>
        <div class="hist-item" *ngFor="let it of d.items">
          <span class="hist-hora">{{ it.hora || '—' }}</span>
          <span class="hist-badge" [ngClass]="claseAccion(it.accion_key)">{{ it.accion }}</span>
          <span class="hist-puesto">
            <span class="hist-puesto-nom">{{ it.puesto || '—' }}</span>
            <span class="hist-cliente" *ngIf="it.cliente && it.cliente !== it.puesto">{{ it.cliente }}</span>
          </span>
          <span class="hist-detalle">
            <ng-container *ngIf="it.accion_key === 'CAMBIO'">
              <span class="hist-antes">{{ it.antes }}</span>
              <span class="hist-flecha">→</span>
              <span class="hist-despues">{{ it.despues }}</span>
            </ng-container>
            <ng-container *ngIf="it.accion_key !== 'CAMBIO'">{{ it.persona }}</ng-container>
          </span>
          <span class="hist-user">{{ it.usuario || '—' }}</span>
        </div>
      </div>
    </mat-dialog-content>
    <mat-dialog-actions align="end">
      <button mat-button (click)="cerrar()">Cerrar</button>
    </mat-dialog-actions>
  `,
  styles: [`
    .hist-content { min-width: 640px; max-width: 820px; max-height: 70vh; }
    .hist-sub { font-weight: 600; color: #374151; margin-bottom: 10px; text-transform: capitalize; }
    .hist-msg { color: #6b7280; padding: 16px 0; text-align: center; }
    .hist-dia { margin-bottom: 14px; }
    .hist-dia-cab {
      font-weight: 700; color: #1f2937; background: #f3f4f6; padding: 5px 10px;
      border-radius: 6px; text-transform: capitalize; display: flex; justify-content: space-between; align-items: center;
    }
    .hist-dia-count { background: #e5e7eb; color: #374151; border-radius: 10px; font-size: 11px; padding: 1px 8px; font-weight: 700; }
    .hist-item {
      display: grid; grid-template-columns: 46px 104px 1.3fr 1.4fr auto; gap: 10px; align-items: center;
      padding: 6px 10px; border-bottom: 1px solid #f1f5f9; font-size: 13px;
    }
    .hist-hora { color: #6b7280; font-variant-numeric: tabular-nums; }
    .hist-badge { font-size: 10px; font-weight: 700; border-radius: 10px; padding: 2px 8px; text-align: center; white-space: nowrap; }
    .acc-create { background: #dcfce7; color: #166534; }
    .acc-update { background: #dbeafe; color: #1e40af; }
    .acc-delete { background: #fee2e2; color: #991b1b; }
    .acc-cambio { background: #ede9fe; color: #6d28d9; }
    .hist-puesto { display: flex; flex-direction: column; line-height: 1.2; }
    .hist-puesto-nom { color: #111827; font-weight: 600; }
    .hist-cliente { color: #6b7280; font-size: 11px; }
    .hist-detalle { color: #111827; }
    .hist-antes { color: #6b7280; }
    .hist-flecha { color: #6d28d9; font-weight: 700; margin: 0 4px; }
    .hist-despues { color: #111827; font-weight: 600; }
    .hist-user { color: #6b7280; font-size: 12px; white-space: nowrap; }
  `],
})
export class HistorialMesDialogComponent implements OnInit {
  cargando = true;
  total = 0;
  dias: HistDia[] = [];
  nombreMes = '';

  private readonly meses = ['', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
    'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre'];

  constructor(
    private asignacionService: AsignacionService,
    private dialogRef: MatDialogRef<HistorialMesDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: { mes: number; anio: number }
  ) {
    this.nombreMes = this.meses[this.data?.mes] || '';
  }

  ngOnInit(): void {
    this.asignacionService.historialMes(this.data.mes, this.data.anio).subscribe({
      next: (res) => {
        this.total = res?.total || 0;
        this.dias = res?.dias || [];
        this.cargando = false;
      },
      error: () => { this.cargando = false; },
    });
  }

  claseAccion(key: string): string {
    if (key === 'CREATE') return 'acc-create';
    if (key === 'DELETE') return 'acc-delete';
    if (key === 'CAMBIO') return 'acc-cambio';
    return 'acc-update';
  }

  formatoDia(iso: string): string {
    // iso = YYYY-MM-DD -> "Lunes 21/09/2026"
    const [y, m, d] = (iso || '').split('-').map(Number);
    if (!y) return iso;
    const fecha = new Date(y, (m || 1) - 1, d || 1);
    const dias = ['Domingo', 'Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado'];
    const nd = dias[fecha.getDay()] || '';
    const dd = String(d).padStart(2, '0');
    const mm = String(m).padStart(2, '0');
    return `${nd} ${dd}/${mm}/${y}`;
  }

  cerrar(): void { this.dialogRef.close(); }
}
