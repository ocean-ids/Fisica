import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatButtonToggle, MatButtonToggleModule } from '@angular/material/button-toggle';
import { ReporteGuardiaService } from '../../services/reporte-guardia.service';
import { ReporteGuardia } from '../../models/reporte-guardia.model';

@Component({
  selector: 'app-reporte-guardia',
  imports: [CommonModule, FormsModule, MatButtonToggleModule],
  templateUrl: './reporte-guardia.component.html',
  styleUrl: './reporte-guardia.component.css',
})
export class ReporteGuardiaComponent implements OnInit {
  filtroFecha = new Date().toISOString().slice(0, 10);   // día/mes/año
  filtroTurno: 'Diurno' | 'Nocturno' = 'Diurno';
  loading = false;
  filas: ReporteGuardia[] = [];

  readonly etiquetas: Record<string, string> = {
    cliente: 'Cliente',
    puesto: 'Puesto',
    persona_nombre: '1 Nombre y 2 Apellidos',
    proviene: 'Proviene',
    valor: 'Valor',
    tipo: 'Tipo',
    autorizacion: 'Autorización',
    motivo: 'Motivo',
    fecha_evento: 'Fecha',
  };

  readonly secciones = [
    { key: 'DOBLADAS',     label: 'DOBLADAS',     cols: ['cliente','puesto','persona_nombre','proviene','valor'], total: true },
    { key: 'ADICIONALES',  label: 'ADICIONALES',  cols: ['cliente','puesto','persona_nombre','proviene'], total: false },
    { key: 'ADELANTOS',    label: 'ADELANTOS',    cols: ['cliente','puesto','persona_nombre','proviene','tipo'], total: false },
    { key: 'NO_CUBIERTOS', label: 'NO CUBIERTOS', cols: ['cliente','puesto','autorizacion','motivo'], total: false },
    { key: 'FALTOS',       label: 'FALTOS',       cols: ['cliente','puesto','persona_nombre','motivo'], total: false },
    { key: 'HUECA',        label: 'HUECA',        cols: ['cliente','puesto','motivo','fecha_evento'], total: false },
    { key: 'APOYO',        label: 'APOYO',        cols: ['cliente','puesto','persona_nombre','proviene','motivo'], total: false },
  ];

  celda(f: any, campo: string): string {
    const v = f?.[campo];
    if (campo === 'valor') return v ? Number(v).toFixed(2) : '';
    return v ?? '';
  }

  totalValor(key: string): number {
    return this.filasDe(key).reduce((s, f) => s + Number(f.valor || 0), 0);
  }

  constructor(private srv: ReporteGuardiaService){}

  ngOnInit(): void {
    this.cargar();
  }

  cargar(): void {
    this.loading = true;
    this.srv.listar(this.filtroFecha, this.filtroTurno).subscribe({
      next: (rows) => { this.filas = rows || []; this.loading = false; },
      error: () => { this.filas = []; this.loading = false; },
    });
  }

  onFechaChange(e: Event): void{
    this.filtroFecha = (e.target as HTMLInputElement).value;
    this.cargar()
  }

  filasDe(seccion: string): ReporteGuardia[] { return this.filas.filter(f => f.seccion === seccion); }
}
