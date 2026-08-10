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

  // numero sugerido para la proxima zona (max + 1)
  nuevaZonaNumero: number | null = null;

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
  zonaAuto = false;            // true cuando la zona se fijo sola por la letra

  // mapa letra -> zona (una letra vive en una sola zona)
  private letraZona: Record<string, { zonaId: number; zonaNombre: string }> = {};

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
      next: (ns) => {
        this.nominativos = ns || [];
        this.loading = false;
        // El mapa letra->zona se arma con la lista COMPLETA (sin búsqueda).
        if (!this.busqueda) this.armarLetraZona(ns || []);
      },
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
    const numero = this.siguienteNumeroZona();
    this.svc.crearZona({ numero, nombre: `ZONA ${numero}` }).subscribe({
      next: () => { this.cargarTodo(); },
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
  private armarLetraZona(ns: Nominativo[]): void {
    const map: Record<string, { zonaId: number; zonaNombre: string }> = {};
    for (const n of ns) {
      const l = (n.letra || '').toUpperCase();
      if (l && !map[l]) map[l] = { zonaId: n.zona, zonaNombre: n.zona_nombre || '' };
    }
    this.letraZona = map;
  }

  // Al escribir la letra: la pasa a mayúscula y, si ya existe, fija su zona sola.
  onLetraChange(): void {
    this.nomLetra = (this.nomLetra || '').toUpperCase();
    const hit = this.letraZona[this.nomLetra];
    if (hit) {
      this.nomZona = hit.zonaId;
      this.zonaAuto = true;
    } else {
      this.zonaAuto = false;
    }
  }

  nuevoNominativo(): void {
    this.nomEditId = null; this.nomZona = this.zonas[0]?.id ?? null;
    this.nomLetra = ''; this.nomNumero = null; this.nomInstalacion = null;
    this.zonaAuto = false;
  }
  editarNominativo(n: Nominativo): void {
    this.nomEditId = n.id; this.nomZona = n.zona; this.nomLetra = n.letra;
    this.nomNumero = n.numero; this.nomInstalacion = n.instalacion;
    this.zonaAuto = false;
  }
  cancelarNominativo(): void { this.nomEditId = null; this.nomZona = null; this.zonaAuto = false; }

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
