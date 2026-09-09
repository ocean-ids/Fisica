import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatDialog, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { EventualService, EventualListItem } from '../../../services/eventual.service';
import { EventualDatosDialogComponent } from '../eventual-datos-dialog/eventual-datos-dialog.component';

@Component({
  selector: 'app-eventuales-lista-dialog',
  standalone: true,
  imports: [CommonModule, FormsModule, MatDialogModule, MatButtonModule],
  template: `
    <h2 mat-dialog-title class="ev-titulo">Eventuales</h2>

    <mat-dialog-content>
      <input class="ev-buscar" type="text" [(ngModel)]="filtro"
             placeholder="Buscar por cédula, nombre o apellido…">

      <div *ngIf="cargando" class="ev-msg">Cargando…</div>

      <div *ngIf="!cargando" class="ev-tabla-wrap">
        <table class="ev-tabla">
          <thead>
            <tr>
              <th>Cédula</th>
              <th>Apellidos y Nombres</th>
              <th>F. Ingreso</th>
              <th>Cuenta</th>
              <th>Banco</th>
              <th>Tipo</th>
              <th>Provincia</th>
            </tr>
          </thead>
          <tbody>
            <tr *ngFor="let e of filtrados()" class="ev-row" (click)="editar(e)"
                title="Clic para ver/editar">
              <td>{{ e.cedula }}</td>
              <td class="ev-nombre">{{ e.apellidos }} {{ e.nombres }}</td>
              <td>{{ e.fecha_ingreso || '-' }}</td>
              <td>{{ e.numero_cuenta || '-' }}</td>
              <td>{{ e.banco || '-' }}</td>
              <td>{{ tipoLabel(e.tipo_cuenta) }}</td>
              <td>{{ e.provincia_nombre || '-' }}</td>
            </tr>
            <tr *ngIf="!filtrados().length">
              <td colspan="7" class="ev-vacio">Sin eventuales</td>
            </tr>
          </tbody>
        </table>
      </div>
    </mat-dialog-content>

    <mat-dialog-actions align="end">
      <button mat-button (click)="cerrar()">Cerrar</button>
    </mat-dialog-actions>
  `,
  styles: [`
    .ev-titulo { text-align: center; }
    mat-dialog-content { min-width: 320px; max-width: 92vw; }
    .ev-buscar {
      width: 100%; box-sizing: border-box; margin-bottom: 12px;
      padding: 8px 12px; border: 1px solid #dce3ea; border-radius: 8px; font-size: 14px;
    }
    .ev-msg, .ev-vacio { text-align: center; color: #5b6b79; padding: 18px; }
    .ev-tabla-wrap { overflow-x: auto; }
    .ev-tabla { width: 100%; border-collapse: collapse; font-size: 13px; white-space: nowrap; }
    .ev-tabla th {
      text-align: center; color: #475569; font-weight: 600; padding: 8px 10px;
      border-bottom: 2px solid #e5e7eb; position: sticky; top: 0; background: #fff;
    }
    .ev-tabla td { padding: 7px 10px; border-bottom: 1px solid #f1f5f9; text-align: center; }
    .ev-nombre { font-weight: 600; }
    .ev-row { cursor: pointer; }
    .ev-row:hover td { background: #eef4f5; }
  `],
})
export class EventualesListaDialogComponent implements OnInit {
  items: EventualListItem[] = [];
  filtro = '';
  cargando = true;

  constructor(
    private dialogRef: MatDialogRef<EventualesListaDialogComponent>,
    private evSvc: EventualService,
    private dialog: MatDialog,
  ) {}

  ngOnInit(): void { this.cargar(); }

  private cargar(): void {
    this.cargando = true;
    this.evSvc.listar().subscribe({
      next: (res) => { this.items = res?.results || []; this.cargando = false; },
      error: () => { this.items = []; this.cargando = false; },
    });
  }

  filtrados(): EventualListItem[] {
    const q = this.filtro.trim().toLowerCase();
    if (!q) return this.items;
    return this.items.filter((e) =>
      (e.cedula || '').toLowerCase().includes(q) ||
      (`${e.apellidos} ${e.nombres}`).toLowerCase().includes(q));
  }

  tipoLabel(t: string): string {
    if (t === 'AHORROS') return 'Ahorros';
    if (t === 'CORRIENTE') return 'Corriente';
    if (t === 'DIGITAL') return 'Digital';
    return '-';
  }

  editar(e: EventualListItem): void {
    const ref = this.dialog.open(EventualDatosDialogComponent, {
      width: '760px', maxWidth: '95vw', data: { personaId: e.persona_id },
    });
    ref.afterClosed().subscribe((changed) => { if (changed) this.cargar(); });
  }

  cerrar(): void { this.dialogRef.close(); }
}
