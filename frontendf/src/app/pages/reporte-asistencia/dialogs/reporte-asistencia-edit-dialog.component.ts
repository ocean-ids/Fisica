import { CommonModule } from '@angular/common';
import { Component, Inject } from '@angular/core';
import { FormBuilder, FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatSelectModule } from '@angular/material/select';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatIconModule } from '@angular/material/icon';
import { ReporteAsistenciaService } from '../../../services/reporte-asistencia.service';
import { ReporteAsistenciaRow, UpdateReporteAsistenciaPayload } from '../../../models';
import { PersonaService } from '../../../services/persona.service';
import { Persona } from '../../../models';
import Swal from 'sweetalert2';


@Component({
  selector: 'app-reporte-asistencia-edit-dialog',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatDialogModule,
    MatAutocompleteModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatSelectModule,
    MatCheckboxModule,
    MatIconModule
  ],
  templateUrl: './reporte-asistencia-edit-dialog.component.html',
  styleUrl: './reporte-asistencia-edit-dialog.component.css'
})
export class ReporteAsistenciaEditDialogComponent {
  // RETEN y CUSTODIO se retiraron: se cuentan en el consolidado por el TIPO del reemplazo.
  // EVENTUAL se retiró: se cuenta solo (por el tipo del reemplazo).
  // FR/TRABAJADO SÍ es manual (se elige aquí y se autocompleta si el reemplazo está en franco).
  readonly estadosDisponibles = ['ADICIONAL', 'ADEL/TURNO', 'DOBLA', 'FR/TRABAJADO'];
  readonly estadosAsistenciaDisponibles: Array<'ASISTIO' | 'FALTO'> = ['ASISTIO', 'FALTO'];
  readonly huecaMotivos = [
    'HUECA POR MOVIMIENTO INTERNO',
    'HUECA POR SACAFRANCO',
    'HUECA POR ADELANTO DE TURNO',
    'HUECA POR UNIDAD FIJA',
    'HUECA POR RENUNCIA',
  ];
  readonly tiposReemplazoPermitidos = new Set(['FIJOS', 'SACAFRANCO','RETEN', 'CUSTODIO', 'EVENTUAL', 'SACAVACACIONES','SUPERVISOR MOTORIZADO', 'SUPERVISOR ZONAL']);
  descripcionesComunes: string[] = [];

  reemplazos: Persona[] = [];
  reemplazoCtrl = new FormControl<Persona | string | null>('');
  reemplazosOcupadosIds = new Set<number>();
  personasAsignadasIds = new Set<number>();
  personasFrancoIds = new Set<number>();
  cargandoReemplazos = false;
  guardando = false;
  error = '';
  form: FormGroup;

  // Dictado por voz (Web Speech API — nativo del navegador, Chrome/Edge)
  soportaDictado = !!((window as any).webkitSpeechRecognition || (window as any).SpeechRecognition);
  dictando = false;
  private recognition?: any;
  private descBase = '';

  constructor(
    private fb: FormBuilder,
    private reporteSvc: ReporteAsistenciaService,
    private personaSvc: PersonaService,
    private dialogRef: MatDialogRef<ReporteAsistenciaEditDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: {
      row: ReporteAsistenciaRow;
      fecha?: string | null;
      occupiedReemplazoIds?: number[];
      assignedPersonaIds?: number[];
      francoPersonaIds?: number[];
    }
  ) {
    this.dialogRef.disableClose = true;
    this.reemplazosOcupadosIds = new Set(
      (data?.occupiedReemplazoIds || [])
        .map((id) => Number(id))
        .filter((id) => Number.isFinite(id) && id > 0)
    );
    // Personas con asignación activa: el backend no permite usarlas como reemplazo.
    this.personasAsignadasIds = new Set(
      (data?.assignedPersonaIds || [])
        .map((id) => Number(id))
        .filter((id) => Number.isFinite(id) && id > 0)
    );
    // Personas en FRANCO ese día: al elegirlas como reemplazo, estado = FR/TRABAJADO.
    this.personasFrancoIds = new Set(
      (data?.francoPersonaIds || [])
        .map((id) => Number(id))
        .filter((id) => Number.isFinite(id) && id > 0)
    );

    this.form = this.fb.group({
      estado: [(data?.row?.estado && data?.row?.estado !== 'TURNO') ? data.row.estado : null, Validators.required],
      estado_asistencia: [data?.row?.estado_asistencia ?? null],
      reemplazo_id: [data?.row?.reemplazo_id ?? null],
      descripcion: [data?.row?.descripcion ?? ''],
      hueca: [data?.row?.hueca ?? false],
      hueca_motivo: [{ value: data?.row?.hueca_motivo ?? '', disabled: !(data?.row?.hueca) }]
    });

    // Al marcar/desmarcar "Hueca" se re-evalúa todo el bloqueo (una hueca no tiene
    // cobertura: se limpia y deshabilita estado/reemplazo, y se habilita el motivo).
    this.form.get('hueca')?.valueChanges.subscribe(() => {
      this.aplicarBloqueoAsistencia(this.form.get('estado_asistencia')?.value, true);
    });

    this.reemplazoCtrl.setValue(data?.row?.reemplazo || '', { emitEvent: false });
    this.reemplazoCtrl.valueChanges.subscribe((value) => {
      if (typeof value === 'string') {
        this.form.get('reemplazo_id')?.setValue(null, { emitEvent: false });
      }
    });

    // Estado y Reemplazo solo se habilitan cuando la asistencia es FALTO.
    // Inicial: solo bloquea/habilita (sin limpiar, para no borrar datos existentes al abrir).
    this.aplicarBloqueoAsistencia(this.form.get('estado_asistencia')?.value, false);
    // Cambio del usuario: si pasa a NO FALTO, además limpia estado y reemplazo.
    this.form.get('estado_asistencia')?.valueChanges.subscribe((v) => {
      this.aplicarBloqueoAsistencia(v, true);
    });
    // Al cambiar el Estado: cambia el filtro del reemplazo, así que se limpia y se re-evalúa
    // (el reemplazo queda deshabilitado hasta elegir un Estado).
    this.form.get('estado')?.valueChanges.subscribe(() => {
      this.reemplazoCtrl.setValue('', { emitEvent: false });
      this.form.get('reemplazo_id')?.setValue(null, { emitEvent: false });
      this.aplicarBloqueoReemplazo();
    });

    this.cargarReemplazos();
    this.cargarDescripciones();
  }

  // Habilita el Estado solo si la asistencia es FALTO.
  // Si no es FALTO: lo deshabilita (y, si el usuario lo cambió, lo limpia).
  private aplicarBloqueoAsistencia(estadoAsistencia: any, limpiar = false): void {
    const esFalto = (estadoAsistencia || '').toString().toUpperCase() === 'FALTO';
    const estadoCtrl = this.form.get('estado');
    const huecaCtrl = this.form.get('hueca');
    const motivoCtrl = this.form.get('hueca_motivo');

    // Estado: se habilita solo si la asistencia es FALTO (regla normal, obligatorio).
    if (esFalto) {
      estadoCtrl?.enable({ emitEvent: false });
    } else {
      if (limpiar) { estadoCtrl?.setValue(null, { emitEvent: false }); }
      estadoCtrl?.disable({ emitEvent: false });
    }

    // Check "Hueca" (extra): solo habilitado si la asistencia es FALTO.
    if (esFalto) {
      huecaCtrl?.enable({ emitEvent: false });
      // Motivo: habilitado solo si la hueca está marcada.
      if (huecaCtrl?.value) {
        motivoCtrl?.enable({ emitEvent: false });
      } else {
        motivoCtrl?.disable({ emitEvent: false });
      }
    } else {
      if (limpiar) {
        huecaCtrl?.setValue(false, { emitEvent: false });
        motivoCtrl?.setValue('', { emitEvent: false });
      }
      huecaCtrl?.disable({ emitEvent: false });
      motivoCtrl?.disable({ emitEvent: false });
    }

    // El reemplazo depende de FALTO Y de tener un Estado elegido (regla normal).
    this.aplicarBloqueoReemplazo(limpiar);
  }

  // Habilita el Reemplazo solo si la asistencia es FALTO y ya se eligió un Estado.
  private aplicarBloqueoReemplazo(limpiar = false): void {
    const esFalto = (this.form.get('estado_asistencia')?.value || '').toString().toUpperCase() === 'FALTO';
    const tieneEstado = !!this.form.get('estado')?.value;
    const reemplazoIdCtrl = this.form.get('reemplazo_id');

    if (esFalto && tieneEstado) {
      reemplazoIdCtrl?.enable({ emitEvent: false });
      this.reemplazoCtrl.enable({ emitEvent: false });
    } else {
      if (limpiar) {
        reemplazoIdCtrl?.setValue(null, { emitEvent: false });
        this.reemplazoCtrl.setValue('', { emitEvent: false });
      }
      reemplazoIdCtrl?.disable({ emitEvent: false });
      this.reemplazoCtrl.disable({ emitEvent: false });
    }
  }

  private cargarDescripciones(): void {
    this.reporteSvc.getDescripciones().subscribe({
      next: (list) => { this.descripcionesComunes = Array.isArray(list) ? list : []; },
      error: () => { this.descripcionesComunes = []; }
    });
  }

  private cargarReemplazos(): void {
    this.cargandoReemplazos = true;
    this.personaSvc.getPersonas().subscribe({
      next: (data) => {
        const list = Array.isArray(data) ? data : [];
        // Incluir también los ocupados: se muestran con estado ASIGNADO (deshabilitados).
        this.reemplazos = list.filter((p) =>
          !!p?.id &&
          p?.is_active !== false &&
          this.tiposReemplazoPermitidos.has(String(p?.tipo || ''))
        );
        // Disponibles primero, luego por nombre.
        this.reemplazos.sort((a, b) => {
          const oa = this.esReemplazoOcupado(a) ? 1 : 0;
          const ob = this.esReemplazoOcupado(b) ? 1 : 0;
          if (oa !== ob) return oa - ob;
          return this.getNombrePersona(a).localeCompare(this.getNombrePersona(b));
        });

        const selectedId = this.form.get('reemplazo_id')?.value;
        if (selectedId) {
          const selectedPersona = this.reemplazos.find(p => p.id === selectedId);
          if (selectedPersona) {
            this.reemplazoCtrl.setValue(selectedPersona, { emitEvent: false });
          }
        }
      },
      error: (err) => {
        console.error('Error al cargar reemplazos', err);
        this.error = 'No se pudo cargar la lista de reemplazos.';
      },
      complete: () => {
        this.cargandoReemplazos = false;
      }
    });
  }


  getNombrePersona(p: Persona): string {
    return `${p.nombres || ''} ${p.apellidos || ''}`.trim();
  }

  esReemplazoOcupado(p: Persona): boolean {
    if (!p?.id) return false;
    // Solo se bloquea si ya está usado como reemplazo en OTRO registro del reporte.
    // Tener asignación activa (puesto) YA NO bloquea: se puede elegir (movimiento interno).
    return this.reemplazosOcupadosIds.has(Number(p.id));
  }

  estadoReemplazo(p: Persona): 'DISPONIBLE' | 'ASIGNADO' | 'EN USO' {
    if (!p?.id) return 'DISPONIBLE';
    const id = Number(p.id);
    if (this.reemplazosOcupadosIds.has(id)) return 'EN USO';    // ya es reemplazo en otro registro (bloqueado)
    if (this.personasAsignadasIds.has(id)) return 'ASIGNADO';   // tiene puesto, pero se puede elegir
    return 'DISPONIBLE';
  }

  // Color del badge según el estado del reemplazo.
  colorReemplazo(p: Persona): string {
    const e = this.estadoReemplazo(p);
    if (e === 'EN USO') return '#dc3545';    // rojo: bloqueado (ya es reemplazo)
    if (e === 'ASIGNADO') return '#d97706';  // ámbar: asignado pero elegible
    return '#198754';                        // verde: disponible
  }

  private normalizeText(value: string | null | undefined): string {
    if (!value) return '';
    return value.toString().trim().toUpperCase().replace(/[^A-Z0-9]+/g, '');
  }

  displayReemplazo = (value: Persona | string | null): string => {
    if (!value) return '';
    if (typeof value === 'string') return value;
    return this.getNombrePersona(value);
  };

  onReemplazoOptionSelected(value: Persona | null): void {
    if (value?.id && this.reemplazosOcupadosIds.has(Number(value.id))) {
      Swal.fire({
        icon: 'warning',
        title: 'Reemplazo ocupado',
        text: 'Esta persona ya esta seleccionada como reemplazo en otro registro del reporte.',
      });
      this.reemplazoCtrl.setValue('', { emitEvent: false });
      this.form.get('reemplazo_id')?.setValue(null);
      return;
    }

    this.form.get('reemplazo_id')?.setValue(value?.id ?? null);

    // Si el reemplazo elegido está en FRANCO ese día, se autocompleta el estado FR/TRABAJADO
    // (queda editable: el usuario puede cambiarlo).
    if (value?.id && this.personasFrancoIds.has(Number(value.id))) {
      this.form.get('estado')?.setValue('FR/TRABAJADO');
    }
  }

  getDescripcionesFiltradas(): string[] {
    const val = (this.form.get('descripcion')?.value || '').toString().trim().toUpperCase();
    if (!val) return this.descripcionesComunes;
    return this.descripcionesComunes.filter(d => (d || '').toUpperCase().includes(val));
  }

  getReemplazosFiltrados(): Persona[] {
    let base = this.reemplazos;
    const estadoActual = (this.form?.value?.estado || '').toString().toUpperCase();
    // En ADICIONAL el reemplazo no puede ser EVENTUAL.
    if (estadoActual === 'ADICIONAL') {
      base = base.filter(p => (p.tipo || '').toString().toUpperCase() !== 'EVENTUAL');
    }

    const currentValue = this.reemplazoCtrl.value;
    const query = typeof currentValue === 'string'
      ? currentValue
      : (currentValue ? this.getNombrePersona(currentValue) : '');
    const q = this.normalizeText(query);
    if (!q) return base;

    return base.filter((p) => {
      const fullName = this.normalizeText(`${p.apellidos || ''} ${p.nombres || ''}`);
      const tipo = this.normalizeText(p.tipo || '');
      return fullName.includes(q) || tipo.includes(q);
    });
  }

  cancelar(): void {
    if (this.guardando) return;
    this.detenerDictado();
    this.dialogRef.close();
  }

  // Dictado por voz sobre el campo Descripción (Web Speech API, nativo del navegador).
  // Escribe lo dictado respetando el texto ya tecleado; se detiene al hacer clic de nuevo.
  toggleDictado(): void {
    const SR = (window as any).webkitSpeechRecognition || (window as any).SpeechRecognition;
    if (!SR) { return; }
    if (this.dictando) {            // ya está escuchando -> detener
      this.detenerDictado();
      return;
    }
    if (!this.recognition) {
      this.recognition = new SR();
      this.recognition.lang = 'es-EC';
      this.recognition.continuous = true;
      this.recognition.interimResults = true;
      this.recognition.onresult = (e: any) => {
        let texto = '';
        for (let i = 0; i < e.results.length; i++) {
          texto += e.results[i][0].transcript;
        }
        const val = (this.descBase ? this.descBase + ' ' : '') + texto;
        this.form.get('descripcion')?.setValue(val.trim());
      };
      this.recognition.onend = () => { this.dictando = false; };
      this.recognition.onerror = () => { this.dictando = false; };
    }
    this.descBase = this.form.get('descripcion')?.value || '';   // conserva lo ya escrito
    this.dictando = true;
    this.recognition.start();       // pide permiso de micrófono la 1ª vez
  }

  private detenerDictado(): void {
    if (this.recognition && this.dictando) {
      try { this.recognition.stop(); } catch { /* noop */ }
    }
    this.dictando = false;
  }

  // Tipo de la persona elegida como reemplazo.
  get reemplazoTipo(): string {
    const id = this.form?.value?.reemplazo_id;
    if (!id) { return ''; }
    const p = this.reemplazos.find(x => x.id === Number(id));
    return (p?.tipo || '').toString().toUpperCase();
  }

  // FALTO sin cobertura completa: falta elegir estado (no TURNO) o reemplazo.
  // Mientras sea true, el botón Guardar queda deshabilitado.
  get coberturaFaltoIncompleta(): boolean {
    const estadoAsistencia = (this.form?.value?.estado_asistencia || '').toString().toUpperCase();
    if (estadoAsistencia !== 'FALTO') { return false; }
    const estado = (this.form?.value?.estado || '').toString().trim().toUpperCase();
    const reemplazoId = this.form?.value?.reemplazo_id;
    return !reemplazoId || !estado || estado === 'TURNO';
  }

  guardar(): void {
    if (this.guardando || this.form.invalid || !this.data?.row?.asignacion_id) return;

    // getRawValue incluye los controles deshabilitados (estado/reemplazo cuando NO es FALTO).
    const raw = this.form.getRawValue();

    // Si la asistencia es FALTO, exigir estado de cobertura y reemplazo antes de guardar.
    const estadoAsistencia = (raw.estado_asistencia || '').toString().toUpperCase();
    if (estadoAsistencia === 'FALTO') {
      const estado = (raw.estado || '').toString().trim().toUpperCase();
      const reemplazoId = raw.reemplazo_id;
      if (!reemplazoId || !estado || estado === 'TURNO') {
        Swal.fire({
          icon: 'warning',
          title: 'Completa la cobertura',
          text: 'Como la asistencia es FALTO, debes elegir el ESTADO (cómo se cubrió: ADICIONAL, DOBLA, etc.) y el REEMPLAZO (quién cubrió) antes de guardar.',
        });
        return;
      }
    }

    // ADICIONAL no puede tener un reemplazo EVENTUAL.
    if ((raw.estado || '').toString().toUpperCase() === 'ADICIONAL'
        && this.reemplazoTipo === 'EVENTUAL') {
      Swal.fire({
        icon: 'warning',
        title: 'Reemplazo no válido para ADICIONAL',
        text: 'En ADICIONAL el reemplazo no puede ser un EVENTUAL.',
      });
      return;
    }

    // Si marca "Hueca", debe elegir un motivo.
    if (raw.hueca && !(raw.hueca_motivo || '').toString().trim()) {
      Swal.fire({
        icon: 'warning',
        title: 'Falta el motivo de la hueca',
        text: 'Marcaste "Hueca", elige el motivo para que se refleje en Reporte de Guardia.',
      });
      return;
    }

    const payload: UpdateReporteAsistenciaPayload = {
      estado: raw.estado || null,
      estado_asistencia: raw.estado_asistencia || null,
      reemplazo_id: raw.reemplazo_id === '' ? null : raw.reemplazo_id,
      descripcion: raw.descripcion === '' ? null : raw.descripcion,
      hueca: !!raw.hueca,
      hueca_motivo: raw.hueca ? (raw.hueca_motivo || null) : null,
      fecha: this.data?.fecha || null
    };

    this.guardando = true;
    this.error = '';

    this.reporteSvc.updateReporteAsistencia(this.data.row.asignacion_id, payload).subscribe({
      next: (res) => {
        this.guardando = false;
        this.dialogRef.close(res);
      },
      error: (err) => {
        this.guardando = false;
        this.error = err?.error?.error || err?.error?.detail || 'No se pudo guardar la actualizacion.';
        Swal.fire({
          icon: 'warning',
          title: 'No se pudo guardar',
          text: this.error,
        });
        console.error('Error al actualizar reporte de asistencia', err);
      }
    });
  }
}
