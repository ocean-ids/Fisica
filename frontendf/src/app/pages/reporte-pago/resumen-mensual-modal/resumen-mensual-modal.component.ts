import { Component, Inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { ReportePagoService } from '../../../services/reporte-pago.service';
import { ReportePago, ResumenMensualPago } from '../../../models/reporte-pago.model';

@Component({
  selector: 'app-resumen-mensual-modal',
  standalone: true,
  imports: [CommonModule, FormsModule, MatDialogModule, MatButtonModule],
  templateUrl: './resumen-mensual-modal.component.html',
  styleUrl: './resumen-mensual-modal.component.css',
})
export class ResumenMensualModalComponent implements OnInit {
  tipos: string[] = [];

  mesSel = new Date().getMonth() + 1;
  anioSel = new Date().getFullYear();
  tipoSel = '';   // '' = todos los tipos de servicio

  resumen: ResumenMensualPago | null = null;
  loadingResumen = false;

  // Desglose de una persona (fila expandible).
  personaExpandidaId: number | null = null;
  detallePersona: ReportePago[] = [];
  loadingDetalle = false;

  readonly meses = [
    { v: 1, n: 'Enero' }, { v: 2, n: 'Febrero' }, { v: 3, n: 'Marzo' }, { v: 4, n: 'Abril' },
    { v: 5, n: 'Mayo' }, { v: 6, n: 'Junio' }, { v: 7, n: 'Julio' }, { v: 8, n: 'Agosto' },
    { v: 9, n: 'Septiembre' }, { v: 10, n: 'Octubre' }, { v: 11, n: 'Noviembre' }, { v: 12, n: 'Diciembre' },
  ];

  constructor(
    private srv: ReportePagoService,
    private dialogRef: MatDialogRef<ResumenMensualModalComponent>,
    @Inject(MAT_DIALOG_DATA) public data: { tipos?: string[] } | null,
  ) {
    this.tipos = data?.tipos || [];
  }

  ngOnInit(): void {
    this.cargarResumen();
  }

  get anios(): number[] {
    const y = new Date().getFullYear();
    return [y - 2, y - 1, y, y + 1];
  }

  cargarResumen(): void {
    this.loadingResumen = true;
    this.resumen = null;
    this.personaExpandidaId = null;
    this.detallePersona = [];
    this.srv.resumenMensual(this.mesSel, this.anioSel, this.tipoSel || undefined).subscribe({
      next: (r) => { this.resumen = r; this.loadingResumen = false; },
      error: () => { this.resumen = null; this.loadingResumen = false; },
    });
  }

  togglePersona(personaId: number | null): void {
    if (!personaId) { return; }
    if (this.personaExpandidaId === personaId) {
      this.personaExpandidaId = null;
      this.detallePersona = [];
      return;
    }
    this.personaExpandidaId = personaId;
    this.detallePersona = [];
    this.loadingDetalle = true;
    this.srv.detallePersonaMes(this.mesSel, this.anioSel, personaId, this.tipoSel || undefined).subscribe({
      next: (rows) => { this.detallePersona = rows || []; this.loadingDetalle = false; },
      error: () => { this.detallePersona = []; this.loadingDetalle = false; },
    });
  }

  num(v: any): number { return Number(v || 0); }

  valorFila(f: ReportePago): number {
    const total = this.num(f.valor_total);
    return total > 0 ? total : this.num(f.valor_calculado);
  }

  cerrar(): void { this.dialogRef.close(); }
}
