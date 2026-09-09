import { Component, Inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import Swal from 'sweetalert2';
import { EventualService, EventualDatos } from '../../../services/eventual.service';
import { UbicacionService } from '../../../services/ubicacion.service';

@Component({
  selector: 'app-eventual-datos-dialog',
  standalone: true,
  imports: [
    CommonModule, FormsModule, MatDialogModule, MatFormFieldModule,
    MatInputModule, MatSelectModule, MatButtonModule,
  ],
  template: `
    <h2 mat-dialog-title>Datos del eventual</h2>

    <mat-dialog-content>
      <div *ngIf="cargando" class="ev-cargando">Cargando…</div>

      <div *ngIf="!cargando && datos" class="ev-grid">
        <!-- Fila 1: Cédula · Nombres · Apellidos -->
        <mat-form-field appearance="outline">
          <mat-label>Cédula</mat-label>
          <input matInput [value]="datos.cedula" readonly>
        </mat-form-field>

        <mat-form-field appearance="outline">
          <mat-label>Nombres</mat-label>
          <input matInput [(ngModel)]="datos.nombres">
        </mat-form-field>

        <mat-form-field appearance="outline">
          <mat-label>Apellidos</mat-label>
          <input matInput [(ngModel)]="datos.apellidos">
        </mat-form-field>

        <!-- Fila 2: Banco · Tipo de cuenta · Cuenta bancaria -->
        <mat-form-field appearance="outline">
          <mat-label>Banco</mat-label>
          <mat-select [(ngModel)]="datos.banco" (selectionChange)="onBancoChange()">
            <mat-option value="">-</mat-option>
            <mat-option *ngFor="let b of bancos" [value]="b">{{ b }}</mat-option>
          </mat-select>
        </mat-form-field>

        <mat-form-field appearance="outline">
          <mat-label>Tipo de cuenta</mat-label>
          <mat-select [(ngModel)]="datos.tipo_cuenta" [disabled]="!datos.banco"
                      (selectionChange)="onTipoCuentaChange()">
            <mat-option value="">-</mat-option>
            <mat-option *ngFor="let t of tiposCuenta" [value]="t.v">{{ t.l }}</mat-option>
          </mat-select>
        </mat-form-field>

        <mat-form-field appearance="outline">
          <mat-label>Cuenta bancaria</mat-label>
          <input matInput [(ngModel)]="datos.numero_cuenta"
                 [disabled]="!datos.banco || !datos.tipo_cuenta"
                 [placeholder]="(!datos.banco || !datos.tipo_cuenta) ? 'Elige banco y tipo primero' : ''">
        </mat-form-field>

        <!-- Fila 3: Provincia · Cantón · Fecha de ingreso -->
        <mat-form-field appearance="outline">
          <mat-label>Provincia</mat-label>
          <mat-select [(ngModel)]="datos.provincia_id" (selectionChange)="onProvinciaChange()">
            <mat-option [value]="null">-</mat-option>
            <mat-option *ngFor="let p of provincias" [value]="p.id">{{ p.nombre }}</mat-option>
          </mat-select>
        </mat-form-field>

        <mat-form-field appearance="outline">
          <mat-label>Cantón</mat-label>
          <mat-select [(ngModel)]="datos.canton_id" [disabled]="!datos.provincia_id">
            <mat-option [value]="null">-</mat-option>
            <mat-option *ngFor="let c of cantones" [value]="c.id">{{ c.nombre }}</mat-option>
          </mat-select>
        </mat-form-field>

        <mat-form-field appearance="outline">
          <mat-label>Fecha de ingreso</mat-label>
          <input matInput type="date" [(ngModel)]="datos.fecha_ingreso">
        </mat-form-field>
      </div>
    </mat-dialog-content>

    <mat-dialog-actions align="end">
      <button mat-button (click)="cerrar()">Cancelar</button>
      <button mat-raised-button color="primary" [disabled]="cargando || guardando" (click)="guardar()">
        Guardar
      </button>
    </mat-dialog-actions>
  `,
  styles: [`
    mat-dialog-content { min-width: 300px; max-width: 760px; }
    .ev-cargando { padding: 24px; text-align: center; color: #5b6b79; }
    .ev-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px 14px; padding-top: 8px; }
    .ev-grid mat-form-field { width: 100%; }
    @media (max-width: 680px) { .ev-grid { grid-template-columns: 1fr 1fr; } }
    @media (max-width: 460px) { .ev-grid { grid-template-columns: 1fr; } }
  `],
})
export class EventualDatosDialogComponent implements OnInit {
  datos: EventualDatos | null = null;
  provincias: { id: number; nombre: string }[] = [];
  cantones: { id: number; nombre: string }[] = [];
  cargando = true;
  guardando = false;
  readonly tiposCuenta = [
    { v: 'AHORROS', l: 'Ahorros' },
    { v: 'CORRIENTE', l: 'Corriente' },
    { v: 'DIGITAL', l: 'Digital' },
  ];
  bancos: string[] = [
    'Banco Pichincha', 'Banco del Pacífico', 'Banco Guayaquil', 'Produbanco',
    'Banco Internacional', 'Banco Bolivariano', 'Banco del Austro', 'Banco de Machala',
    'Banco ProCredit', 'Banco Solidario', 'Banco General Rumiñahui', 'Banco Amazonas',
    'Banco del Litoral', 'Banco Coopnacional', 'Banco Capital', 'BanEcuador',
    'Cooperativa JEP', 'Cooperativa Jardín Azuayo', 'Cooperativa Policía Nacional',
    'Cooperativa 29 de Octubre', 'Cooperativa Cooprogreso', 'Cooperativa Alianza del Valle',
  ];

  constructor(
    private dialogRef: MatDialogRef<EventualDatosDialogComponent>,
    private evSvc: EventualService,
    private ubicacionSvc: UbicacionService,
    @Inject(MAT_DIALOG_DATA) public data: { personaId: number },
  ) {}

  ngOnInit(): void {
    this.ubicacionSvc.getProvincias().subscribe({
      next: (list: any[]) => { this.provincias = (list || []).map(p => ({ id: p.id, nombre: p.nombre })); },
      error: () => { this.provincias = []; },
    });
    this.evSvc.obtener(this.data.personaId).subscribe({
      next: (d) => {
        this.datos = d;
        this.cargando = false;
        // Si el banco guardado no está en la lista, se agrega para que se vea seleccionado.
        const b = (d.banco || '').trim();
        if (b && !this.bancos.includes(b)) { this.bancos = [b, ...this.bancos]; }
        if (d.provincia_id) { this.cargarCantones(d.provincia_id); }
      },
      error: () => {
        this.cargando = false;
        Swal.fire({ icon: 'error', title: 'Error', text: 'No se pudieron cargar los datos del eventual' });
        this.dialogRef.close();
      },
    });
  }

  private cargarCantones(provinciaId: number): void {
    this.ubicacionSvc.getCantones(provinciaId).subscribe({
      next: (list: any[]) => { this.cantones = (list || []).map(c => ({ id: c.id, nombre: c.nombre })); },
      error: () => { this.cantones = []; },
    });
  }

  onProvinciaChange(): void {
    if (!this.datos) { return; }
    this.cantones = [];
    this.datos.canton_id = null;
    if (this.datos.provincia_id) { this.cargarCantones(this.datos.provincia_id); }
  }

  // Cascada: al cambiar el banco, se reinician tipo de cuenta y número.
  onBancoChange(): void {
    if (!this.datos) { return; }
    if (!this.datos.banco) {
      this.datos.tipo_cuenta = '';
      this.datos.numero_cuenta = '';
    }
  }

  // Al cambiar el tipo de cuenta, se reinicia el número.
  onTipoCuentaChange(): void {
    if (!this.datos) { return; }
    if (!this.datos.tipo_cuenta) {
      this.datos.numero_cuenta = '';
    }
  }

  guardar(): void {
    if (!this.datos) return;
    this.guardando = true;
    const payload: Partial<EventualDatos> = {
      nombres: this.datos.nombres,
      apellidos: this.datos.apellidos,
      fecha_ingreso: this.datos.fecha_ingreso,
      provincia_id: this.datos.provincia_id,
      banco: this.datos.banco,
      numero_cuenta: this.datos.numero_cuenta,
      tipo_cuenta: this.datos.tipo_cuenta,
    };
    // El backend espera 'provincia'/'canton' (no los *_id) para escribir.
    (payload as any).provincia = this.datos.provincia_id;
    (payload as any).canton = this.datos.canton_id;
    this.evSvc.guardar(this.data.personaId, payload).subscribe({
      next: () => {
        this.guardando = false;
        Swal.fire({ icon: 'success', title: 'Guardado', timer: 1000, showConfirmButton: false });
        this.dialogRef.close(true);
      },
      error: (err) => {
        this.guardando = false;
        const msg = err?.error?.error || 'No se pudo guardar';
        Swal.fire({ icon: 'error', title: 'Error', text: msg });
      },
    });
  }

  cerrar(): void {
    this.dialogRef.close();
  }
}
