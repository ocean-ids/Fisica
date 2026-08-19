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
  filtroZona: number | null = null;   // null = todas las zonas

  // numero sugerido para la proxima zona (max + 1)
  nuevaZonaNumero: number | null = null;

  // edicion de zona
  zonaEditId: number | null = null;
  zonaEditNumero: number | null = null;
  zonaEditNombre = '';

  // crear ZONA DE AGRUPACION (agrupa nominativos existentes; al borrarla, vuelven)
  modoAgrupacion = false;
  agrupNombre = '';
  agrupSel = new Set<number>();

  // form nominativo (crear/editar)
  nomEditId: number | null = null;
  nomZona: number | null = null;
  nomLetra = '';
  nomNumero: number | null = null;
  nomInstalacion: number | null = null;
  zonaAuto = false;            // true cuando la zona se fijo sola por la letra

  // mapa letra -> zona (una letra vive en una sola zona)
  private letraZona: Record<string, { zonaId: number; zonaNombre: string }> = {};
  // mapa letra -> numeros ya usados (para sugerir el hueco más bajo)
  private letraNumeros: Record<string, number[]> = {};
  // ids de instalaciones que YA tienen nominativo (para no ofrecerlas al crear)
  private instalacionesConNom = new Set<number>();

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
    // Lista que se muestra (respeta la búsqueda).
    this.svc.getNominativos({ q: this.busqueda || undefined }).subscribe({
      next: (ns) => { this.nominativos = ns || []; this.loading = false; },
      error: () => { this.nominativos = []; this.loading = false; },
    });
    // Mapa letra->zona y números usados: SIEMPRE con la lista COMPLETA (sin búsqueda),
    // para que al borrar un nominativo el número quede realmente libre (reutilizable).
    this.svc.getNominativos().subscribe({
      next: (all) => this.armarLetraZona(all || []),
      error: () => {},
    });
  }

  buscar(): void {
    this.svc.getNominativos({ q: this.busqueda || undefined }).subscribe({
      next: (ns) => { this.nominativos = ns || []; },
      error: () => { this.nominativos = []; },
    });
  }

  // Lista mostrada: aplica el filtro por zona (null = todas) y ordena por
  // LETRA y luego NÚMERO (A1, A2, A10, D24…).
  get nominativosFiltrados(): Nominativo[] {
    const base = this.filtroZona == null
      ? this.nominativos
      : this.nominativos.filter(n => n.zona === this.filtroZona);
    return [...base].sort((a, b) => {
      const la = (a.letra || '').toUpperCase();
      const lb = (b.letra || '').toUpperCase();
      if (la !== lb) return la.localeCompare(lb);
      return (a.numero || 0) - (b.numero || 0);
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

  // ---- Zona de AGRUPACION ----
  abrirAgrupacion(): void {
    this.modoAgrupacion = true; this.agrupNombre = ''; this.agrupSel = new Set<number>();
  }
  cancelarAgrupacion(): void {
    this.modoAgrupacion = false; this.agrupNombre = ''; this.agrupSel = new Set<number>();
  }
  toggleAgrup(id: number): void {
    if (this.agrupSel.has(id)) this.agrupSel.delete(id); else this.agrupSel.add(id);
  }
  crearAgrupacion(): void {
    const ids = Array.from(this.agrupSel);
    if (!ids.length) { Swal.fire('Selecciona nominativos', 'Elige al menos uno para agrupar', 'info'); return; }
    const numero = this.siguienteNumeroZona();
    const nombre = (this.agrupNombre || '').trim() || `AGRUPACION ${numero}`;
    this.svc.crearZona({ numero, nombre, es_agrupacion: true, nominativo_ids: ids }).subscribe({
      next: (res: any) => {
        Swal.fire('Zona de agrupación creada',
          `${res?.nominativos_movidos ?? ids.length} nominativo(s) agrupados. Al borrar esta zona volverán a su zona original.`,
          'success');
        this.cancelarAgrupacion();
        this.cargarTodo();
      },
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
    Swal.fire({
      title: `¿Borrar ${z.nombre}?`,
      text: z.es_agrupacion
        ? 'Es una zona de agrupación: sus nominativos volverán a su zona original.'
        : undefined,
      icon: 'warning', showCancelButton: true, confirmButtonText: 'Borrar',
    }).then(r => { if (r.isConfirmed) {
        this.svc.eliminarZona(z.id).subscribe({
          next: (res: any) => { if (res?.message) Swal.fire('Listo', res.message, 'success'); this.cargarTodo(); },
          error: (e) => this.err(e),
        });
      }});
  }

  // ------------- NOMINATIVOS -------------
  private armarLetraZona(ns: Nominativo[]): void {
    // Zonas de AGRUPACION: son temporales y NO definen la zona real de una letra.
    const agrupIds = new Set((this.zonas || []).filter(z => z.es_agrupacion).map(z => z.id));
    const mapZ: Record<string, { zonaId: number; zonaNombre: string }> = {};
    const mapN: Record<string, number[]> = {};
    const conNom = new Set<number>();
    for (const n of ns) {
      const l = (n.letra || '').toUpperCase();
      const enAgrup = agrupIds.has(n.zona);
      // Solo cuentan como "usados" los nominativos ligados a una instalación.
      // Un nominativo libre (sin instalación) NO tapa el número -> queda reutilizable.
      if (l && n.instalacion != null) {
        // La zona de la letra la definen SOLO las zonas NORMALES (no las de agrupación),
        // así al mover una letra a una agrupación el selector no se bloquea en esa zona.
        if (!enAgrup && !mapZ[l]) mapZ[l] = { zonaId: n.zona, zonaNombre: n.zona_nombre || '' };
        // El número SIEMPRE cuenta como usado (aunque esté en agrupación) para no repetir código.
        (mapN[l] = mapN[l] || []).push(n.numero);
      }
      if (n.instalacion != null) conNom.add(n.instalacion);
    }
    this.letraZona = mapZ;
    this.letraNumeros = mapN;
    this.instalacionesConNom = conNom;
  }

  // Solo instalaciones SIN nominativo (libres). Al editar, incluye también la que ya
  // tiene este nominativo para que quede seleccionada.
  get instalacionesLibres(): any[] {
    // Solo instalaciones ACTIVAS y sin nominativo. Las CERRADAS (activo=false) no se
    // ofrecen (vuelven a aparecer al reabrirlas). Se mantiene la ya seleccionada al editar.
    return this.instalaciones.filter(
      (i) => (i.activo !== false && !this.instalacionesConNom.has(i.id)) || i.id === this.nomInstalacion
    );
  }

  // Devuelve el numero más bajo disponible para la letra (rellena huecos: si borraste
  // el 15, vuelve a proponer 15; si no hay huecos, el siguiente).
  private siguienteNumeroLetra(letra: string): number {
    const usados = new Set(this.letraNumeros[letra] || []);
    let n = 1;
    while (usados.has(n)) n++;
    return n;
  }

  // Al escribir la letra: la pasa a mayúscula, fija la zona (si existe) y sugiere el
  // número automático (hueco más bajo). Solo autocompleta el número al CREAR.
  onLetraChange(): void {
    this.nomLetra = (this.nomLetra || '').toUpperCase();
    const hit = this.letraZona[this.nomLetra];
    const agrupIds = new Set((this.zonas || []).filter(z => z.es_agrupacion).map(z => z.id));
    // Solo se auto-fija/bloquea la zona si la letra ya vive en una zona NORMAL.
    // Si su única presencia es en una agrupación, el usuario puede elegir la zona.
    if (hit && !agrupIds.has(hit.zonaId)) {
      this.nomZona = hit.zonaId;
      this.zonaAuto = true;
    } else {
      this.zonaAuto = false;
    }
    if (!this.nomEditId) {
      this.nomNumero = this.nomLetra ? this.siguienteNumeroLetra(this.nomLetra) : null;
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

  // Habilita Guardar solo cuando TODOS los campos están completos (incluida instalación).
  puedeGuardarNominativo(): boolean {
    return !!(this.nomZona && this.nomLetra && this.nomNumero != null && this.nomInstalacion);
  }

  guardarNominativo(): void {
    if (!this.puedeGuardarNominativo()) {
      Swal.fire('Faltan datos', 'Completa zona, letra, número e instalación', 'info'); return;
    }
    const payload = {
      zona: this.nomZona!, letra: this.nomLetra, numero: this.nomNumero!,
      instalacion: this.nomInstalacion!,
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
