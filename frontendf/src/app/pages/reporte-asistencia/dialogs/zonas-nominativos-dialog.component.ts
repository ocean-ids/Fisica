import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import Swal from 'sweetalert2';
import { NominativoService, ZonaOperativa, Nominativo } from '../../../services/nominativo.service';
import { InstalacionService } from '../../../services/instalacion.service';

@Component({
  selector: 'app-zonas-nominativos-dialog',
  standalone: true,
  imports: [CommonModule, FormsModule, MatDialogModule],
  templateUrl: './zonas-nominativos-dialog.component.html',
  styleUrl: './zonas-nominativos-dialog.component.css',
})
export class ZonasNominativosDialogComponent implements OnInit {
  zonas: ZonaOperativa[] = [];
  nominativos: Nominativo[] = [];
  instalaciones: any[] = [];
  loading = false;
  busqueda = '';

  // form zona nueva
  nuevaZonaNumero: number | null = null;
  nuevaZonaNombre = '';

  // edicion de zona
  zonaEditId: number | null = null;
  zonaEditNumero: number | null = null;
  zonaEditNombre = '';

  // form nominativo (crear/editar)
  nomEditId: number | null = null;
  nomZona: number | null = null;
  nomLetra = '';
  nomNumero: number | null = null;
  nomInstalacion: number | null = null;

  constructor(
    private ref: MatDialogRef<ZonasNominativosDialogComponent>,
    private svc: NominativoService,
    private instSvc: InstalacionService,
  ) {}

  ngOnInit(): void {
    this.cargarTodo();
    this.instSvc.getInstalaciones().subscribe({
      next: (list) => { this.instaciones(list); },
      error: () => { this.instalaciones = []; },
    });
  }

  private instaciones(list: any[]) {
    this.instalaciones = (list || []).sort((a, b) =>
      String(a.codigo || '').localeCompare(String(b.codigo || '')));
  }

  private siguienteNumeroZona(): number {
    const max = this.zonas.reduce((m, z) => Math.max(m, z.numero || 0), 0);
    return max + 1;
  }

  cargarTodo(): void {
    this.loading = true;
    this.svc.getZonas().subscribe({
      next: (zs) => { this.zonas = zs || []; this.nuevaZonaNumero = this.siguienteNumeroZona(); },
      error: () => { this.zonas = []; },
    });
    this.svc.getNominativos({ q: this.busqueda || undefined }).subscribe({
      next: (ns) => { this.nominativos = ns || []; this.loading = false; },
      error: () => { this.nominativos = []; this.loading = false; },
    });
  }

  buscar(): void {
    this.svc.getNominativos({ q: this.busqueda || undefined }).subscribe({
      next: (ns) => { this.nominativos = ns || []; },
      error: () => { this.nominativos = []; },
    });
  }

  private err(e: any): void {
    const msg = e?.error?.error || 'Ocurrió un error';
    Swal.fire('No se pudo', msg, 'warning');
  }

  // ---------------- ZONAS ----------------
  crearZona(): void {
    if (this.nuevaZonaNumero == null) { Swal.fire('Falta', 'Indica el número de zona', 'info'); return; }
    this.svc.crearZona({ numero: this.nuevaZonaNumero, nombre: this.nuevaZonaNombre }).subscribe({
      next: () => { this.nuevaZonaNombre = ''; this.cargarTodo(); },
      error: (e) => this.err(e),
    });
  }

  editarZona(z: ZonaOperativa): void {
    this.zonaEditId = z.id; this.zonaEditNumero = z.numero; this.zonaEditNombre = z.nombre;
  }
  cancelarEditZona(): void { this.zonaEditId = null; }
  guardarZona(): void {
    if (this.zonaEditId == null) return;
    this.svc.actualizarZona(this.zonaEditId, { numero: this.zonaEditNumero ?? undefined, nombre: this.zonaEditNombre })
      .subscribe({ next: () => { this.zonaEditId = null; this.cargarTodo(); }, error: (e) => this.err(e) });
  }
  borrarZona(z: ZonaOperativa): void {
    Swal.fire({ title: `¿Borrar ${z.nombre}?`, icon: 'warning', showCancelButton: true, confirmButtonText: 'Borrar' })
      .then(r => { if (r.isConfirmed) {
        this.svc.eliminarZona(z.id).subscribe({ next: () => this.cargarTodo(), error: (e) => this.err(e) });
      }});
  }

  // ------------- NOMINATIVOS -------------
  nuevoNominativo(): void {
    this.nomEditId = null; this.nomZona = this.zonas[0]?.id ?? null;
    this.nomLetra = ''; this.nomNumero = null; this.nomInstalacion = null;
  }
  editarNominativo(n: Nominativo): void {
    this.nomEditId = n.id; this.nomZona = n.zona; this.nomLetra = n.letra;
    this.nomNumero = n.numero; this.nomInstalacion = n.instalacion;
  }
  cancelarNominativo(): void { this.nomEditId = null; this.nomZona = null; }

  guardarNominativo(): void {
    if (!this.nomZona || !this.nomLetra || this.nomNumero == null) {
      Swal.fire('Faltan datos', 'Zona, letra y número son obligatorios', 'info'); return;
    }
    const payload = {
      zona: this.nomZona, letra: this.nomLetra, numero: this.nomNumero,
      instalacion: this.nomInstalacion || null,
    };
    const obs = this.nomEditId
      ? this.svc.actualizarNominativo(this.nomEditId, payload)
      : this.svc.crearNominativo(payload);
    obs.subscribe({
      next: () => { this.cancelarNominativo(); this.nomZona = null; this.cargarTodo(); },
      error: (e) => this.err(e),
    });
  }

  borrarNominativo(n: Nominativo): void {
    Swal.fire({ title: `¿Borrar ${n.codigo}?`, icon: 'warning', showCancelButton: true, confirmButtonText: 'Borrar' })
      .then(r => { if (r.isConfirmed) {
        this.svc.eliminarNominativo(n.id).subscribe({ next: () => this.cargarTodo(), error: (e) => this.err(e) });
      }});
  }

  cerrar(): void { this.ref.close(); }
}
