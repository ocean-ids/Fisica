import { CommonModule } from '@angular/common';
import { Component, Inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { MatChipsModule } from '@angular/material/chips';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { InstalacionService } from '../../services/instalacion.service';
import { UbicacionService } from '../../services/ubicacion.service';

export interface CantonOption {
  id: number | null;
  nombre: string;
}

export type VistaTipo = 'canton' | 'cliente' | 'persona_tipo';

export const TIPOS_PERSONA: string[] = [
  'FIJOS', 'RETEN', 'CUSTODIO', 'EVENTUAL', 'SACAFRANCO', 'SACAVACACIONES',
  'SUPERVISOR ZONAL', 'SUPERVISOR EVENTUAL', 'SUPERVISOR MOTORIZADO',
  'SUPERVISOR DE ACOMPAÑAMIENTO', 'OPERADOR CENTRO CONTROL', 'SUPERVISOR CENTRO CONTROL',
];

export interface CantonMixView {
  id: string;
  nombre: string;
  tipo: VistaTipo;
  cantonIds: number[];
  clienteIds: number[];
  instalacionIds: number[];
  tipos: string[];
}

export interface CantonViewsModalData {
  cantones: CantonOption[];
  empresas: CantonOption[];
  views: CantonMixView[];
}

export interface CantonViewsModalResult {
  views: CantonMixView[];
}

@Component({
  selector: 'app-canton-views-modal',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatAutocompleteModule,
    MatChipsModule,
    MatIconModule,
    MatButtonModule,
  ],
  template: `
    <h2 mat-dialog-title>Nueva Vista</h2>
    <mat-dialog-content>
      <!-- Selector de tipo de vista -->
      <div class="tipo-toggle-wrap mb-3">
        <div class="tipo-toggle">
          <button type="button"
            [class.active]="tipo === 'canton'"
            (click)="setTipo('canton')">Por cantones</button>
          <button type="button"
            [class.active]="tipo === 'cliente'"
            (click)="setTipo('cliente')">Por empresas</button>
          <button type="button"
            [class.active]="tipo === 'persona_tipo'"
            (click)="setTipo('persona_tipo')">Por tipo</button>
        </div>
      </div>

      <mat-form-field class="w-100" appearance="outline">
        <mat-label>Nombre de la vista</mat-label>
        <input matInput [(ngModel)]="viewName" placeholder="Ej: GUAYAQUIL - DURÁN" />
      </mat-form-field>

      @if (tipo === 'persona_tipo') {
        <mat-form-field class="w-100" appearance="outline">
          <mat-label>Tipos seleccionados</mat-label>
          <mat-chip-grid #chipGridT aria-label="Seleccion de tipos de persona">
            @for (t of selectedTipos; track t) {
              <mat-chip-row (removed)="removeTipo(t)">
                {{ t }}
                <button matChipRemove [attr.aria-label]="'Quitar ' + t">
                  <mat-icon>cancel</mat-icon>
                </button>
              </mat-chip-row>
            }
          </mat-chip-grid>
          <input
            placeholder="Buscar tipo..."
            [(ngModel)]="query"
            [matChipInputFor]="chipGridT"
            [matAutocomplete]="autoTipo"
          />
          <mat-autocomplete #autoTipo="matAutocomplete" (optionSelected)="addTipo($event.option.value)">
            @for (t of filteredTipos; track t) {
              <mat-option [value]="t">{{ t }}</mat-option>
            }
          </mat-autocomplete>
        </mat-form-field>
      } @else if (tipo === 'canton') {
        <mat-form-field class="w-100" appearance="outline">
          <mat-label>Cantones seleccionados</mat-label>
          <mat-chip-grid #chipGrid aria-label="Seleccion de cantones">
            @for (id of selectedCantonIds; track id) {
              <mat-chip-row (removed)="removeCanton(id)">
                {{ getName('canton', id) }}
                <button matChipRemove [attr.aria-label]="'Quitar ' + getName('canton', id)">
                  <mat-icon>cancel</mat-icon>
                </button>
              </mat-chip-row>
            }
          </mat-chip-grid>
          <input
            placeholder="Buscar canton..."
            [(ngModel)]="query"
            [matChipInputFor]="chipGrid"
            [matAutocomplete]="autoCanton"
          />
          <mat-autocomplete #autoCanton="matAutocomplete" (optionSelected)="addCanton($event.option.value)">
            @for (c of filteredCantones; track c.id) {
              <mat-option [value]="c.id">{{ c.nombre }}</mat-option>
            }
          </mat-autocomplete>
        </mat-form-field>
      } @else {
        <!-- 1) Empresa: se elige UNA (solo para ver sus instalaciones); no lleva chips -->
        <mat-form-field class="w-100" appearance="outline">
          <mat-label>Empresa</mat-label>
          <input
            matInput
            placeholder="Buscar empresa..."
            [(ngModel)]="empresaModel"
            [matAutocomplete]="autoCliente"
          />
          <mat-autocomplete #autoCliente="matAutocomplete"
            (optionSelected)="onSelectEmpresa($event.option.value)"
            [displayWith]="displayEmpresa">
            @for (c of filteredEmpresas; track c.id) {
              <mat-option [value]="c.id">{{ c.nombre }}</mat-option>
            }
          </mat-autocomplete>
        </mat-form-field>

        <!-- 2) Instalaciones: chips (acumulan de varias empresas). El desplegable muestra
             las de la empresa elegida arriba; para agregar de otra, cambia la empresa. -->
        @if (empresaActivaId != null || selectedInstalaciones.length || selectedEmpresasToda.length) {
          <div class="hint-inst">Elige instalaciones específicas o agrega <b>toda la empresa</b>. Cambia de empresa arriba para agregar de otra.</div>
          <mat-form-field class="w-100" appearance="outline">
            <mat-label>Instalaciones seleccionadas</mat-label>
            <mat-chip-grid #chipGridI aria-label="Seleccion de instalaciones">
              @for (eid of selectedEmpresasToda; track eid) {
                <mat-chip-row (removed)="removeEmpresaToda(eid)">
                  {{ getName('cliente', eid) }} <small class="text-muted">· TODA LA EMPRESA</small>
                  <button matChipRemove [attr.aria-label]="'Quitar ' + getName('cliente', eid)">
                    <mat-icon>cancel</mat-icon>
                  </button>
                </mat-chip-row>
              }
              @for (i of selectedInstalaciones; track i.id) {
                <mat-chip-row (removed)="removeInstalacion(i.id)">
                  {{ i.nombre }} <small class="text-muted">· {{ getName('cliente', i.empresaId) }}</small>
                  <button matChipRemove [attr.aria-label]="'Quitar ' + i.nombre">
                    <mat-icon>cancel</mat-icon>
                  </button>
                </mat-chip-row>
              }
            </mat-chip-grid>
            <input
              [placeholder]="cargandoInstalaciones ? 'Cargando...' : (empresaActivaId == null ? 'Elige una empresa arriba' : 'Buscar instalación o (Toda la empresa)...')"
              [(ngModel)]="query"
              [matChipInputFor]="chipGridI"
              [matAutocomplete]="autoInst"
            />
            <mat-autocomplete #autoInst="matAutocomplete" (optionSelected)="onInstOption($event.option.value)">
              @if (empresaActivaId != null && !selectedEmpresasToda.includes(empresaActivaId)) {
                <mat-option [value]="'__TODA__'">➤ Toda la empresa ({{ getName('cliente', empresaActivaId) }})</mat-option>
              }
              @for (i of filteredInstalaciones; track i.id) {
                <mat-option [value]="i.id">{{ i.nombre }}</mat-option>
              }
            </mat-autocomplete>
          </mat-form-field>
        }
      }

      <div class="d-flex gap-2 mb-3">
        <button mat-flat-button color="primary" type="button" (click)="saveView()">Guardar vista</button>
        <button mat-stroked-button type="button" (click)="resetForm()">Limpiar</button>
      </div>

      @if (views.length) {
        <div class="saved-list">
          <div class="fw-semibold mb-2">Vistas guardadas</div>
          @for (v of views; track v.id) {
            <div class="saved-item">
              <div class="saved-title">
                {{ v.nombre }}
                <span class="badge-tipo">{{ v.tipo === 'cliente' ? 'EMPRESAS' : (v.tipo === 'persona_tipo' ? 'TIPOS' : 'CANTONES') }}</span>
              </div>
              <div class="saved-chips">
                @if (v.tipo === 'cliente') {
                  @for (id of v.clienteIds; track id) {
                    <span class="saved-chip">{{ getName('cliente', id) }}</span>
                  }
                  @if (v.instalacionIds && v.instalacionIds.length) {
                    <span class="saved-chip saved-chip-inst">{{ v.instalacionIds.length }} instalación(es)</span>
                  } @else {
                    <span class="saved-chip saved-chip-inst">toda la empresa</span>
                  }
                } @else if (v.tipo === 'persona_tipo') {
                  @for (t of v.tipos; track t) {
                    <span class="saved-chip">{{ t }}</span>
                  }
                } @else {
                  @for (id of v.cantonIds; track id) {
                    <span class="saved-chip">{{ getName('canton', id) }}</span>
                  }
                }
              </div>
              <div class="d-flex gap-2 mt-2">
                <button mat-stroked-button color="primary" type="button" (click)="editView(v)">Editar</button>
                <button mat-stroked-button color="warn" type="button" (click)="deleteView(v.id)">Eliminar</button>
              </div>
            </div>
          }
        </div>
      }
    </mat-dialog-content>

    <mat-dialog-actions adockerlign="end">
      <button mat-stroked-button type="button" (click)="close()">Cerrar</button>
    </mat-dialog-actions>
  `,
  styles: [
    `
    .tipo-toggle-wrap { display: flex; justify-content: center; }
    .tipo-toggle { display: inline-flex; border: 1px solid #c7d2fe; border-radius: 999px; overflow: hidden; }
    .tipo-toggle button { border: none; background: #fff; padding: 6px 16px; font-size: 13px; cursor: pointer; color: #4338ca; }
    .tipo-toggle button.active { background: #4338ca; color: #fff; }
    .saved-list { border-top: 1px solid #e5e7eb; padding-top: 12px; }
    .saved-item { border: 1px solid #e5e7eb; border-radius: 8px; padding: 10px; margin-bottom: 10px; }
    .saved-title { font-weight: 600; display: flex; align-items: center; gap: 8px; }
    .badge-tipo { font-size: 10px; font-weight: 700; background: #eef2ff; color: #4338ca; border: 1px solid #c7d2fe; border-radius: 999px; padding: 1px 8px; }
    .saved-chips { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 6px; }
    .saved-chip { background: #eef2ff; border: 1px solid #c7d2fe; border-radius: 999px; padding: 2px 8px; font-size: 12px; }
    .saved-chip-inst { background: #ecfdf5; border-color: #a7f3d0; color: #047857; }
    .hint-inst { font-size: 12px; color: #6b7280; margin: -4px 0 8px; }
    `
  ]
})
export class CantonViewsModalComponent {
  views: CantonMixView[] = [];
  viewName = '';
  tipo: VistaTipo = 'canton';
  selectedCantonIds: number[] = [];
  selectedTipos: string[] = [];
  // Vista por empresa: se elige UNA empresa (para ver sus instalaciones) y se agregan
  // instalaciones específicas como chips. Se repite con otras empresas; las empresas de
  // la vista se derivan de las instalaciones elegidas.
  empresaModel: number | string | null = null;   // id (empresa activa) o texto (buscando)
  empresaActivaId: number | null = null;          // empresa cuyas instalaciones se muestran
  instalacionesActiva: { id: number; nombre: string }[] = [];  // instalaciones de la empresa activa
  // Chips: instalaciones elegidas (de una o varias empresas), con su empresa.
  selectedInstalaciones: { id: number; nombre: string; empresaId: number }[] = [];
  // Empresas agregadas COMPLETAS ("toda la empresa", sin instalaciones específicas).
  selectedEmpresasToda: number[] = [];
  cargandoInstalaciones = false;
  readonly tiposDisponibles = TIPOS_PERSONA;
  query = '';
  editingId: string | null = null;
  // Lista completa de cantones (la carga el propio modal para no depender de la
  // vista actualmente cargada en la pantalla de asignaciones).
  cantonesAll: CantonOption[] = [];

  constructor(
    private dialogRef: MatDialogRef<CantonViewsModalComponent, CantonViewsModalResult>,
    private instalacionService: InstalacionService,
    private ubicacionService: UbicacionService,
    @Inject(MAT_DIALOG_DATA) public data: CantonViewsModalData,
  ) {
    this.cantonesAll = (data?.cantones || []).slice();
    // Cargar TODOS los cantones (independiente de la vista activa).
    this.ubicacionService.getCantones().subscribe({
      next: (data: any[]) => {
        const lista = (data || [])
          .map(c => ({ id: c.id, nombre: c.nombre } as CantonOption))
          .filter(c => c.id != null && c.nombre);
        if (lista.length) this.cantonesAll = lista;
      },
      error: () => {}
    });
    this.views = (data?.views || []).map(v => ({
      ...v,
      tipo: v.tipo || 'canton',
      cantonIds: v.cantonIds || [],
      clienteIds: v.clienteIds || [],
      instalacionIds: v.instalacionIds || [],
      tipos: v.tipos || [],
    }));
  }

  get filteredTipos(): string[] {
    const q = (this.query || '').trim().toLowerCase();
    return this.tiposDisponibles
      .filter(t => !this.selectedTipos.includes(t))
      .filter(t => !q || t.toLowerCase().includes(q));
  }

  addTipo(t: string): void {
    if (!t || this.selectedTipos.includes(t)) return;
    this.selectedTipos = [...this.selectedTipos, t];
    this.query = '';
  }

  removeTipo(t: string): void {
    this.selectedTipos = this.selectedTipos.filter(x => x !== t);
  }

  setTipo(t: VistaTipo): void {
    if (this.tipo === t) return;
    this.tipo = t;
    this.query = '';
  }

  private filterOptions(source: CantonOption[], excludeIds: number[]): CantonOption[] {
    const q = (this.query || '').trim().toLowerCase();
    return (source || [])
      .filter(c => c.id != null)
      .filter(c => !excludeIds.includes(c.id as number))
      .filter(c => !q || (c.nombre || '').toLowerCase().includes(q));
  }

  get filteredCantones(): CantonOption[] {
    return this.filterOptions(this.cantonesAll || [], this.selectedCantonIds);
  }

  // Empresas que coinciden con el texto escrito (autocomplete de una sola empresa activa).
  get filteredEmpresas(): CantonOption[] {
    const v = this.empresaModel;
    const q = (typeof v === 'string' ? v : '').trim().toLowerCase();
    return (this.data?.empresas || [])
      .filter(c => c.id != null)
      .filter(c => !q || (c.nombre || '').toLowerCase().includes(q));
  }

  // Muestra el nombre cuando el modelo es un id; deja el texto cuando se está buscando.
  displayEmpresa = (value: number | string | null): string => {
    if (value == null || value === '') return '';
    if (typeof value === 'number') return this.getName('cliente', value);
    return String(value);
  };

  // Instalaciones de la EMPRESA ACTIVA aún no elegidas, filtradas por texto.
  get filteredInstalaciones(): { id: number; nombre: string }[] {
    const q = (this.query || '').trim().toLowerCase();
    const yaId = new Set(this.selectedInstalaciones.map(i => i.id));
    return (this.instalacionesActiva || [])
      .filter(i => !yaId.has(i.id))
      .filter(i => !q || (i.nombre || '').toLowerCase().includes(q));
  }

  getName(tipo: VistaTipo, id: number): string {
    const source = tipo === 'cliente' ? (this.data?.empresas || []) : (this.cantonesAll || []);
    const c = source.find(x => x.id === id);
    return c?.nombre || `${tipo === 'cliente' ? 'EMPRESA' : 'CANTON'} ${id}`;
  }

  getInstName(id: number): string {
    const i = this.selectedInstalaciones.find(x => x.id === id);
    return i?.nombre || `INSTALACION ${id}`;
  }

  addCanton(id: number): void {
    if (!id || this.selectedCantonIds.includes(id)) return;
    this.selectedCantonIds = [...this.selectedCantonIds, id];
    this.query = '';
  }

  removeCanton(id: number): void {
    this.selectedCantonIds = this.selectedCantonIds.filter(x => x !== id);
  }

  // Elegir empresa: se vuelve la empresa activa y se cargan SUS instalaciones para el
  // desplegable. NO borra los chips ya elegidos de otras empresas.
  onSelectEmpresa(id: number): void {
    if (!id) return;
    this.empresaActivaId = id;
    this.empresaModel = id;
    this.instalacionesActiva = [];
    this.query = '';
    this.cargarInstalacionesActiva(id);
  }

  // Carga las instalaciones de una empresa.
  //  - modo normal: las pone como opciones de la empresa activa (para elegir).
  //  - esEdicion=true: repone lo guardado -> chips de las instalaciones de ESTA empresa que
  //    estén en preset; si la empresa no tiene ninguna en preset, se marca como "toda la empresa".
  private cargarInstalacionesActiva(clienteId: number, preset?: number[], esEdicion = false): void {
    if (!clienteId) return;
    this.cargandoInstalaciones = true;
    this.instalacionService.getInstalaciones({ cliente_id: clienteId }).subscribe({
      next: (data: any[]) => {
        const nuevas = (data || []).map(i => ({ id: i.id, nombre: i.nombre || `Instalación ${i.id}` }));
        // Si es la empresa activa, poblar el desplegable (evita que una carga vieja lo pise).
        if (this.empresaActivaId === clienteId) {
          this.instalacionesActiva = nuevas;
        }
        if (esEdicion) {
          const validos = new Set(nuevas.map(i => i.id));
          const yaId = new Set(this.selectedInstalaciones.map(i => i.id));
          const chips = (preset || [])
            .filter(pid => validos.has(pid) && !yaId.has(pid))
            .map(pid => ({ id: pid, nombre: nuevas.find(n => n.id === pid)?.nombre || `INSTALACION ${pid}`, empresaId: clienteId }));
          if (chips.length) {
            this.selectedInstalaciones = [...this.selectedInstalaciones, ...chips];
          } else if (!this.selectedEmpresasToda.includes(clienteId)) {
            // Sin instalaciones específicas de esta empresa en la vista -> toda la empresa.
            this.selectedEmpresasToda = [...this.selectedEmpresasToda, clienteId];
          }
        }
        this.cargandoInstalaciones = false;
      },
      error: () => { this.cargandoInstalaciones = false; }
    });
  }

  // Opción elegida del desplegable de instalaciones: instalación específica o "toda la empresa".
  onInstOption(value: any): void {
    if (value === '__TODA__') { this.addEmpresaToda(this.empresaActivaId); return; }
    this.addInstalacion(value);
  }

  addInstalacion(id: number): void {
    if (!id || this.empresaActivaId == null) return;
    if (this.selectedInstalaciones.some(i => i.id === id)) return;
    const inst = (this.instalacionesActiva || []).find(i => i.id === id);
    if (!inst) return;
    this.selectedInstalaciones = [...this.selectedInstalaciones, { id: inst.id, nombre: inst.nombre, empresaId: this.empresaActivaId }];
    // Si la empresa estaba como "toda", pasa a instalaciones específicas.
    this.selectedEmpresasToda = this.selectedEmpresasToda.filter(x => x !== this.empresaActivaId);
    this.query = '';
  }

  removeInstalacion(id: number): void {
    this.selectedInstalaciones = this.selectedInstalaciones.filter(x => x.id !== id);
  }

  // Agregar la empresa completa (toda la empresa): quita sus instalaciones específicas.
  addEmpresaToda(eid: number | null): void {
    if (eid == null || this.selectedEmpresasToda.includes(eid)) return;
    this.selectedEmpresasToda = [...this.selectedEmpresasToda, eid];
    this.selectedInstalaciones = this.selectedInstalaciones.filter(i => i.empresaId !== eid);
    this.query = '';
  }

  removeEmpresaToda(eid: number): void {
    this.selectedEmpresasToda = this.selectedEmpresasToda.filter(x => x !== eid);
  }

  saveView(): void {
    const nombre = (this.viewName || '').trim();
    if (!nombre) return;
    if (this.tipo === 'canton' && this.selectedCantonIds.length < 1) return;
    if (this.tipo === 'cliente' && (this.selectedInstalaciones.length + this.selectedEmpresasToda.length) < 1) return;
    if (this.tipo === 'persona_tipo' && this.selectedTipos.length < 1) return;

    // Empresas de la vista = empresas de las instalaciones elegidas + empresas "toda" (sin repetir).
    const empresasDeInst = this.selectedInstalaciones.map(i => i.empresaId);
    const clienteIds = Array.from(new Set([...empresasDeInst, ...this.selectedEmpresasToda]));

    const nueva: Omit<CantonMixView, 'id'> = {
      nombre,
      tipo: this.tipo,
      cantonIds: this.tipo === 'canton' ? [...this.selectedCantonIds] : [],
      clienteIds: this.tipo === 'cliente' ? clienteIds : [],
      instalacionIds: this.tipo === 'cliente' ? this.selectedInstalaciones.map(i => i.id) : [],
      tipos: this.tipo === 'persona_tipo' ? [...this.selectedTipos] : [],
    };

    if (this.editingId) {
      this.views = this.views.map(v => v.id === this.editingId ? { ...v, ...nueva } : v);
    } else {
      this.views = [...this.views, { id: `view_${Date.now()}`, ...nueva }];
    }
    this.resetForm();
  }

  editView(v: CantonMixView): void {
    this.editingId = v.id;
    this.viewName = v.nombre;
    this.tipo = v.tipo || 'canton';
    this.selectedCantonIds = [...(v.cantonIds || [])];
    this.selectedTipos = [...(v.tipos || [])];
    this.selectedInstalaciones = [];
    this.selectedEmpresasToda = [];
    this.instalacionesActiva = [];
    // Empresa activa = la primera de la vista (para que el desplegable muestre sus instalaciones).
    this.empresaActivaId = (v.clienteIds && v.clienteIds.length) ? v.clienteIds[0] : null;
    this.empresaModel = this.empresaActivaId;
    // Reponer por empresa: chips de las instalaciones guardadas, o "toda la empresa" si no tenía.
    const preset = [...(v.instalacionIds || [])];
    for (const cid of (v.clienteIds || [])) {
      this.cargarInstalacionesActiva(cid, preset, true);
    }
  }

  deleteView(id: string): void {
    this.views = this.views.filter(v => v.id !== id);
    if (this.editingId === id) {
      this.resetForm();
    }
  }

  resetForm(): void {
    this.editingId = null;
    this.viewName = '';
    this.selectedCantonIds = [];
    this.selectedTipos = [];
    this.empresaModel = null;
    this.empresaActivaId = null;
    this.instalacionesActiva = [];
    this.selectedInstalaciones = [];
    this.selectedEmpresasToda = [];
    this.cargandoInstalaciones = false;
    this.query = '';
  }

  close(): void {
    this.dialogRef.close({ views: this.views });
  }
}
