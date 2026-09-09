import { Component, Inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import Swal from 'sweetalert2';
import { NotificacionService, NotificacionEventual } from '../../services/notificacion.service';

interface EventualEditable {
  notifId: number;
  cedula: string;
  nombres: string;
  apellidos: string;
  tipo: string;
}

@Component({
  selector: 'app-validar-eventuales-dialog',
  standalone: true,
  imports: [
    CommonModule, FormsModule, MatDialogModule, MatFormFieldModule,
    MatInputModule, MatSelectModule, MatButtonModule, MatIconModule, MatProgressBarModule,
  ],
  template: `
    <h2 mat-dialog-title>Eventuales por validar</h2>
    <mat-dialog-content>
      <ng-container *ngIf="current as it; else vacio">
        <div class="ve-counter">
          <span>Eventual <b>{{ done + 1 }}</b> de <b>{{ total }}</b></span>
          <span class="ve-restantes">{{ items.length }} por revisar</span>
        </div>
        <mat-progress-bar mode="determinate" [value]="(done / total) * 100"></mat-progress-bar>

        <p class="ve-intro">Revisa los datos. Corrige lo que esté mal y confirma.</p>

        <div class="ve-card">
          <div class="ve-grid">
            <mat-form-field appearance="outline">
              <mat-label>Cédula</mat-label>
              <input matInput [(ngModel)]="it.cedula" maxlength="10" inputmode="numeric"
                     (keydown)="soloNumeros($event)">
            </mat-form-field>

            <mat-form-field appearance="outline">
              <mat-label>Tipo</mat-label>
              <mat-select [(ngModel)]="it.tipo">
                <mat-option *ngFor="let t of tipos" [value]="t">{{ t }}</mat-option>
              </mat-select>
            </mat-form-field>

            <mat-form-field appearance="outline">
              <mat-label>Nombres</mat-label>
              <input matInput [(ngModel)]="it.nombres">
            </mat-form-field>

            <mat-form-field appearance="outline">
              <mat-label>Apellidos</mat-label>
              <input matInput [(ngModel)]="it.apellidos">
            </mat-form-field>
          </div>

          <div class="ve-actions">
            <button mat-stroked-button *ngIf="items.length > 1" [disabled]="guardando" (click)="saltar()">
              Saltar
            </button>
            <button mat-raised-button color="primary"
                    [disabled]="guardando || !it.cedula || !it.nombres || !it.apellidos"
                    (click)="confirmar(it)">
              <mat-icon>check</mat-icon> Confirmar
            </button>
          </div>
        </div>
      </ng-container>

      <ng-template #vacio>
        <p class="ve-vacio">No hay eventuales por validar. 🎉</p>
      </ng-template>
    </mat-dialog-content>

    <mat-dialog-actions align="end">
      <button mat-button (click)="cerrar()">Cerrar</button>
    </mat-dialog-actions>
  `,
  styles: [`
    :host { display: block; }
    mat-dialog-content { max-width: 560px; }
    .ve-counter {
      display: flex; justify-content: space-between; align-items: baseline;
      font-size: 0.95rem; color: #14202b; margin-bottom: 6px;
    }
    .ve-counter b { color: #0e7c86; }
    .ve-restantes { font-size: 0.8rem; color: #5b6b79; }
    .ve-intro { color: #5b6b79; font-size: 0.88rem; margin: 12px 0 10px; }
    .ve-card {
      border: 1px solid #dce3ea; border-radius: 10px; padding: 14px 12px 8px; background: #f8fafc;
    }
    .ve-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px 14px; }
    .ve-grid mat-form-field { width: 100%; }
    .ve-actions { display: flex; justify-content: flex-end; gap: 10px; margin-top: 2px; }
    .ve-vacio { text-align: center; color: #1a8a5c; font-weight: 600; padding: 24px 0; }
    @media (max-width: 560px) { .ve-grid { grid-template-columns: 1fr; } }
  `],
})
export class ValidarEventualesDialogComponent {
  items: EventualEditable[] = [];
  index = 0;          // posición actual en la cola
  done = 0;           // cuántos ya se validaron
  total = 0;          // total inicial
  guardando = false;

  readonly tipos = [
    'FIJOS', 'RETEN', 'CUSTODIO', 'EVENTUAL', 'SACAFRANCO', 'SACAVACACIONES',
    'SUPERVISOR ZONAL', 'SUPERVISOR EVENTUAL', 'SUPERVISOR MOTORIZADO',
    'SUPERVISOR DE ACOMPAÑAMIENTO', 'OPERADOR CENTRO CONTROL', 'SUPERVISOR CENTRO CONTROL',
  ];

  constructor(
    private dialogRef: MatDialogRef<ValidarEventualesDialogComponent>,
    private notifSvc: NotificacionService,
    @Inject(MAT_DIALOG_DATA) public data: { notificaciones: NotificacionEventual[] },
  ) {
    this.items = (data?.notificaciones || []).map((n) => ({
      notifId: n.id,
      cedula: n.persona?.cedula || '',
      nombres: n.persona?.nombres || '',
      apellidos: n.persona?.apellidos || '',
      tipo: n.persona?.tipo || 'EVENTUAL',
    }));
    this.total = this.items.length;
  }

  get current(): EventualEditable | null {
    return this.items[this.index] || null;
  }

  soloNumeros(event: KeyboardEvent): void {
    if (event.key.length > 1 || event.ctrlKey || event.metaKey) return;
    if (!/[0-9]/.test(event.key)) event.preventDefault();
  }

  // Pasa el actual al final de la cola para revisarlo después.
  saltar(): void {
    if (this.items.length <= 1) return;
    const [it] = this.items.splice(this.index, 1);
    this.items.push(it);
    if (this.index >= this.items.length) this.index = 0;
  }

  confirmar(it: EventualEditable): void {
    this.guardando = true;
    this.notifSvc.confirmar(it.notifId, {
      cedula: it.cedula,
      nombres: it.nombres,
      apellidos: it.apellidos,
      tipo: it.tipo,
    }).subscribe({
      next: () => {
        this.guardando = false;
        this.items.splice(this.index, 1);
        this.done++;
        if (this.index >= this.items.length) this.index = Math.max(0, this.items.length - 1);
        Swal.fire({ icon: 'success', title: 'Eventual validado', timer: 900, showConfirmButton: false });
        if (!this.items.length) this.dialogRef.close(true);
      },
      error: (err) => {
        this.guardando = false;
        const msg = err?.error?.error || 'No se pudo validar';
        Swal.fire({ icon: 'error', title: 'Error', text: msg });
      },
    });
  }

  cerrar(): void {
    this.dialogRef.close();
  }
}
