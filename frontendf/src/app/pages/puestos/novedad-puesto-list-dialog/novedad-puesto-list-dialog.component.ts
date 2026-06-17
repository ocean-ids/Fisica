import { Component, Inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatDialogModule, MatDialogRef, MAT_DIALOG_DATA } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { NovedadPuesto } from '../../../models/novedad-puesto.model';
import { NovedadPuestoService } from '../../../services/novedad-puesto.service';

interface DialogData {
  fecha?: string; // fecha cualquiera dentro del mes a mostrar
}

interface DiaGrupo {
  fecha: string;
  label: string;
  diurnos: NovedadPuesto[];
  nocturnos: NovedadPuesto[];
}

@Component({
  selector: 'app-novedad-puesto-list-dialog',
  standalone: true,
  imports: [CommonModule, FormsModule, MatDialogModule, MatButtonModule, MatIconModule],
  templateUrl: './novedad-puesto-list-dialog.component.html',
  styleUrl: './novedad-puesto-list-dialog.component.css'
})
export class NovedadPuestoListDialogComponent implements OnInit {
  cargando = false;
  grupos: DiaGrupo[] = [];
  anio = 0;
  mes = 0;
  mesLabel = '';

  private meses = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
    'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];
  private dias = ['domingo', 'lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado'];

  constructor(
    private dialogRef: MatDialogRef<NovedadPuestoListDialogComponent>,
    private novedadService: NovedadPuestoService,
    @Inject(MAT_DIALOG_DATA) public data: DialogData | null
  ) {}

  ngOnInit(): void {
    const base = this.data?.fecha ? new Date(this.data.fecha + 'T00:00:00') : new Date();
    this.anio = base.getFullYear();
    this.mes = base.getMonth() + 1;
    this.mesLabel = `${this.meses[this.mes - 1]} de ${this.anio}`;
    this.cargar();
  }

  private pad(n: number): string { return String(n).padStart(2, '0'); }

  cargar(): void {
    this.cargando = true;
    const desde = `${this.anio}-${this.pad(this.mes)}-01`;
    const ultimoDia = new Date(this.anio, this.mes, 0).getDate();
    const hasta = `${this.anio}-${this.pad(this.mes)}-${this.pad(ultimoDia)}`;

    this.novedadService.getNovedades({ desde, hasta }).subscribe({
      next: (lista) => {
        this.grupos = this.agrupar(lista || []);
        this.cargando = false;
      },
      error: () => {
        this.grupos = [];
        this.cargando = false;
      }
    });
  }

  private agrupar(lista: NovedadPuesto[]): DiaGrupo[] {
    const map = new Map<string, DiaGrupo>();
    for (const n of lista) {
      const f = n.fecha;
      if (!map.has(f)) {
        const d = new Date(f + 'T00:00:00');
        const label = `${this.dias[d.getDay()]}, ${d.getDate()} de ${this.meses[d.getMonth()]}`;
        map.set(f, { fecha: f, label, diurnos: [], nocturnos: [] });
      }
      const g = map.get(f)!;
      if ((n.turno || '').toLowerCase().startsWith('n')) g.nocturnos.push(n);
      else g.diurnos.push(n);
    }
    return Array.from(map.values()).sort((a, b) => a.fecha.localeCompare(b.fecha));
  }

  get totalRegistros(): number {
    return this.grupos.reduce((acc, g) => acc + g.diurnos.length + g.nocturnos.length, 0);
  }

  cerrar(): void {
    this.dialogRef.close();
  }
}
