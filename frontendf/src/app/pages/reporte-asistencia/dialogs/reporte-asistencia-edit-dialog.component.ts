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
import { ReporteAsistenciaRow } from '../../../models';
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
  // FR/TRABAJADO SÍ es manual (se elige aquí y se autocompleta si el reemplazo está en franco).
  // EVENTUAL: al elegirlo, el reemplazo se filtra a personas tipo EVENTUAL; en Reporte de
  // Guardia el falto va a FALTOS y el eventual a DOBLADAS (proviene = EVENTUAL).
  readonly estadosDisponibles = ['ADICIONAL', 'ADEL/TURNO', 'DOBLA', 'EVENTUAL', 'FR/TRABAJADO'];
  readonly estadosAsistenciaDisponibles: Array<'ASISTIO' | 'FALTO'> = ['ASISTIO', 'FALTO'];
  readonly huecaMotivos = [
    'HUECA POR ADELANTO DE TURNO',
    'HUECA POR UNIDAD FIJA',
    'HUECA POR RENUNCIA',
  ];
  readonly tiposReemplazoPermitidos = new Set(['FIJOS', 'SACAFRANCO','RETEN', 'CUSTODIO', 'EVENTUAL', 'SACAVACACIONES','SUPERVISOR MOTORIZADO', 'SUPERVISOR ZONAL', 'SUPERVISOR EVENTUAL']);
  descripcionesComunes: string[] = [];

  reemplazos: Persona[] = [];
  reemplazoCtrl = new FormControl<Persona | string | null>('');
  // Persona que cubre una HUECA (se muestra en "Apellidos y Nombres"). Solo para huecas.
  coberturaCtrl = new FormControl<Persona | string | null>('');
  coberturaSel: number | null = null;
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
    // Al cambiar el MOTIVO de la hueca: si es "ADELANTO DE TURNO" se habilita el Estado
    // y se fija en ADEL/TURNO; con cualquier otro motivo el Estado se deshabilita.
    this.form.get('hueca_motivo')?.valueChanges.subscribe(() => {
      if (this.esHuecaEstructural) {
        this.aplicarBloqueoAsistencia(this.form.get('estado_asistencia')?.value, false);
      }
    });

    this.reemplazoCtrl.setValue(data?.row?.reemplazo || '', { emitEvent: false });
    this.reemplazoCtrl.valueChanges.subscribe((value) => {
      if (typeof value === 'string') {
        this.form.get('reemplazo_id')?.setValue(null, { emitEvent: false });
      }
    });

    // Precargar la persona de cobertura / guardia del día (si ya había una ese día).
    // En filas normales, "Apellidos y Nombres" ES el selector: muestra el nombre actual
    // (titular o el guardia del día ya elegido) para poder cambiarlo.
    this.coberturaSel = (data?.row as any)?.persona_cobertura_id ?? null;
    if (this.esFilaNormal || this.coberturaSel) {
      this.coberturaCtrl.setValue(data?.row?.nombre_apellidos || '', { emitEvent: false });
    }
    this.coberturaCtrl.valueChanges.subscribe((value) => {
      // Si el usuario escribe texto (no eligió opción), se limpia la selección.
      if (typeof value === 'string') { this.coberturaSel = null; }
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

    // HUECA estructural: la fila sigue siendo "HUECA" (nombre solo lectura). Aquí:
    // - Asistencia: OPCIONAL y habilitada (se puede marcar ASISTE/FALTÓ para que se
    //   refleje en la reportería; no obliga a nada).
    // - Check "Hueca": marcado por defecto.
    // - Motivo y Reemplazo: HABILITADOS y OBLIGATORIOS (sin reemplazo no deja guardar).
    if (this.esHuecaEstructural) {
      const asisCtrl = this.form.get('estado_asistencia');
      asisCtrl?.enable({ emitEvent: false });
      // El Estado se HABILITA en cualquier hueca CON motivo (todas las opciones), y queda
      // en "Seleccione" hasta que el usuario escoja. Sin motivo elegido, se deshabilita.
      const motivoAct = (motivoCtrl?.value || '').toString().trim().toUpperCase();
      if (motivoAct) {
        estadoCtrl?.enable({ emitEvent: false });
      } else {
        estadoCtrl?.setValue(null, { emitEvent: false });
        estadoCtrl?.disable({ emitEvent: false });
      }
      estadoCtrl?.clearValidators();
      estadoCtrl?.updateValueAndValidity({ emitEvent: false });
      // Check "Hueca" marcado por defecto.
      if (!huecaCtrl?.value) { huecaCtrl?.setValue(true, { emitEvent: false }); }
      huecaCtrl?.enable({ emitEvent: false });
      motivoCtrl?.enable({ emitEvent: false });
      // Orden: Motivo -> Estado -> Reemplazo. El Reemplazo se habilita solo cuando ya
      // hay un Estado elegido (igual que en las filas normales).
      this.aplicarBloqueoReemplazo(limpiar);
      return;
    }

    // Check "Hueca" en filas normales: OPCIONAL, disponible solo cuando la asistencia es
    // FALTÓ (el puesto pudo quedar hueco ese día). Desmarcado por defecto; el motivo es
    // opcional. Si no es FALTÓ, no aplica: se desmarca y deshabilita.
    if (esFalto) {
      huecaCtrl?.enable({ emitEvent: false });
    } else {
      huecaCtrl?.setValue(false, { emitEvent: false });
      huecaCtrl?.disable({ emitEvent: false });
    }
    const esHueca = !!huecaCtrl?.value;

    // Estado: habilitado si es FALTO (NO se bloquea por hueca; se puede usar igual).
    if (esFalto) {
      estadoCtrl?.enable({ emitEvent: false });
    } else {
      if (limpiar) { estadoCtrl?.setValue(null, { emitEvent: false }); }
      estadoCtrl?.disable({ emitEvent: false });
    }
    // Obligatorio SOLO si es FALTO y NO es hueca (una hueca no obliga a estado/reemplazo,
    // pero se pueden llenar igual si la hueca sí tuvo cobertura).
    if (esFalto && !esHueca && !this.esSacafranco) {
      estadoCtrl?.setValidators([Validators.required]);
    } else {
      estadoCtrl?.clearValidators();
    }
    estadoCtrl?.updateValueAndValidity({ emitEvent: false });

    // Motivo de la hueca: habilitado solo cuando la hueca está marcada.
    if (esHueca) {
      motivoCtrl?.enable({ emitEvent: false });
    } else {
      if (limpiar) { motivoCtrl?.setValue('', { emitEvent: false }); }
      motivoCtrl?.disable({ emitEvent: false });
    }

    // El reemplazo depende de FALTO y de tener un Estado elegido (regla normal).
    this.aplicarBloqueoReemplazo(limpiar);
  }

  // Habilita el Reemplazo cuando ya se eligió un Estado (ADICIONAL, DOBLA, etc.).
  // El Estado solo se puede elegir con asistencia FALTO, así que basta con tener Estado.
  private aplicarBloqueoReemplazo(limpiar = false): void {
    const tieneEstado = !!this.form.get('estado')?.value;
    const reemplazoIdCtrl = this.form.get('reemplazo_id');

    if (tieneEstado) {
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

  // Apellidos primero (para el selector "Apellidos y Nombres").
  getApellidosNombres(p: Persona): string {
    return `${p.apellidos || ''} ${p.nombres || ''}`.trim();
  }

  // Display del selector de guardia del día: apellidos primero (o el texto tal cual).
  displayCobertura = (value: Persona | string | null): string => {
    if (!value) return '';
    if (typeof value === 'string') return value;
    return this.getApellidosNombres(value);
  };

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
    if (e === 'ASIGNADO') return '#0891b2';  // celeste: movimiento interno (asignado, elegible)
    return '#198754';                        // verde: disponible
  }

  private normalizeText(value: string | null | undefined): string {
    if (!value) return '';
    // NFD separa los acentos en marcas combinantes; el replace final las elimina
    // (no son A-Z0-9), asi "Hernán" -> "HERNAN".
    return value.toString().trim().toUpperCase()
      .normalize('NFD')
      .replace(/[^A-Z0-9]+/g, '');
  }

  displayReemplazo = (value: Persona | string | null): string => {
    if (!value) return '';
    if (typeof value === 'string') return value;
    return this.getNombrePersona(value);
  };

  // Limpia el buscador de Reemplazo (la X): borra texto y el reemplazo elegido.
  limpiarReemplazo(): void {
    this.reemplazoCtrl.setValue('', { emitEvent: false });
    this.form.get('reemplazo_id')?.setValue(null);
  }

  // HUECA: elegir / limpiar la persona que cubre (se muestra en "Apellidos y Nombres").
  onCoberturaOptionSelected(value: Persona | null): void {
    this.coberturaSel = value?.id ?? null;
    // Al elegir a la persona que cubre la hueca, se marca ASISTE automáticamente.
    if (value?.id) {
      this.form.get('estado_asistencia')?.setValue('ASISTIO');
    }
  }
  limpiarCobertura(): void {
    this.coberturaCtrl.setValue('', { emitEvent: false });
    this.coberturaSel = null;
  }

  // Volver al titular: quita el guardia del día elegido (movimiento interno). Al guardar,
  // persona_cobertura queda null y el reporte vuelve a mostrar al titular.
  volverATitular(): void {
    this.coberturaSel = null;
    this.coberturaCtrl.setValue('', { emitEvent: false });
  }

  // Etiqueta del estado del reemplazo. "ASIGNADO" (tiene puesto) se muestra como
  // "MOVIMIENTO INTERNO" en el Reporte de Asistencia (es lo que ocurre al usarlo aquí).
  etiquetaEstadoReemplazo(p: Persona): string {
    const e = this.estadoReemplazo(p);
    return e === 'ASIGNADO' ? 'MOVIMIENTO INTERNO' : e;
  }

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
    const currentValue = this.reemplazoCtrl.value;
    const query = typeof currentValue === 'string'
      ? currentValue
      : (currentValue ? this.getNombrePersona(currentValue) : '');
    let base = this.filtrarPersonas(query);
    // Estado EVENTUAL: el reemplazo debe ser una persona de tipo EVENTUAL.
    const estado = (this.form.get('estado')?.value || '').toString().trim().toUpperCase();
    if (estado === 'EVENTUAL') {
      base = base.filter(p => String(p?.tipo || '').toUpperCase() === 'EVENTUAL');
    }
    return base;
  }

  // Selector de "Apellidos y Nombres" (movimiento interno): personal operativo que se
  // puede mover a este puesto. FIJOS solo si YA tienen asignación (un puesto). SACAFRANCO
  // siempre (trabajan por su ficha de sacafranco, no por Asignacion, así que no entran en
  // personasAsignadasIds pero igual son operativos).
  getCoberturaFiltrados(): Persona[] {
    const v = this.coberturaCtrl.value;
    const query = typeof v === 'string' ? v : (v ? this.getNombrePersona(v) : '');
    return this.filtrarPersonas(query).filter((p) => {
      const tipo = String(p?.tipo || '').toUpperCase();
      if (tipo === 'SACAFRANCO') { return true; }
      if (tipo === 'FIJOS') { return !!p?.id && this.personasAsignadasIds.has(Number(p.id)); }
      return false;
    });
  }

  // ¿Se muestra el badge "MOVIMIENTO INTERNO" para esta persona en el selector?
  // Sí para fijos con asignación (titulares de otro puesto) y para sacafrancos.
  esMovimientoInterno(p: Persona): boolean {
    const tipo = String(p?.tipo || '').toUpperCase();
    if (tipo === 'SACAFRANCO') { return true; }
    return !!p?.id && this.personasAsignadasIds.has(Number(p.id));
  }

  private filtrarPersonas(query: string): Persona[] {
    const base = this.reemplazos;
    // Separar por espacios ANTES de normalizar (normalizeText quita los espacios).
    // Cada palabra debe estar en "nombres apellidos cedula tipo" (en cualquier orden),
    // asi "hector castro" (primer nombre + primer apellido) tambien coincide.
    const tokens = (query || '')
      .split(/\s+/)
      .map(t => this.normalizeText(t))
      .filter(Boolean);
    if (!tokens.length) return base;
    return base.filter((p) => {
      const hay = this.normalizeText(
        `${p.nombres || ''} ${p.apellidos || ''} ${p.cedula || ''} ${p.tipo || ''}`
      );
      return tokens.every(t => hay.includes(t));
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
        const val = (this.descBase ? this.descBase + ' ' : '') + texto.toUpperCase();
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
  get esSacafranco(): boolean {
    return !this.data?.row?.asignacion_id && !!this.data?.row?.sacafranco_fila_id;
  }

  // HUECA estructural: puesto sin persona fija ese dia (nombre "HUECA"). Se permite
  // asignarle una persona (cobertura) y marcar ASISTE SOLO en el reporte de ese dia;
  // no toca Asignaciones, asi que el dia siguiente vuelve a salir HUECA.
  get esHuecaEstructural(): boolean {
    const r: any = this.data?.row;
    const esNombreHueca = (r?.nombre_apellidos || '').toString().trim().toUpperCase() === 'HUECA';
    // Fijo: es_hueca (backend: puesto sin persona) o el nombre "HUECA". Se usa es_hueca
    // porque una hueca ya cubierta muestra el nombre de la persona, no "HUECA".
    if (r?.asignacion_id) {
      return !!r?.es_hueca || esNombreHueca;
    }
    // Sacafranco: solo es hueca cuando la fila NO tiene persona (sale como "HUECA").
    // Un sacafranco con persona asignada NO es hueca: se marca su asistencia normal.
    if (r?.sacafranco_fila_id) {
      return esNombreHueca;
    }
    return false;
  }

  // Opciones de Asistencia: en una hueca solo se permite FALTÓ (no ASISTE).
  get asistenciasDisponibles(): Array<'ASISTIO' | 'FALTO'> {
    return this.esHuecaEstructural ? ['FALTO'] : this.estadosAsistenciaDisponibles;
  }

  // Fila normal (puesto con titular, ni hueca ni sacafranco): permite MOVIMIENTO INTERNO
  // (cambiar el guardia del día solo en el reporte, sin tocar la asignación).
  get esFilaNormal(): boolean {
    return !!this.data?.row?.asignacion_id && !this.esHuecaEstructural && !this.esSacafranco;
  }

  // El botón Guardar se habilita solo cuando el formulario tiene lo mínimo:
  // - Primero hay que marcar la ASISTENCIA (ASISTE o FALTÓ).
  // - Si es FALTÓ (normal), además el estado (cómo se cubrió) y el reemplazo.
  // - Si marca Hueca, exige el motivo.
  get puedeGuardar(): boolean {
    if (this.guardando) { return false; }
    const raw = this.form?.getRawValue?.() || ({} as any);

    // HUECA estructural: exige MOTIVO y REEMPLAZO (sin reemplazo no deja guardar).
    if (this.esHuecaEstructural) {
      const tieneMotivo = !!(raw.hueca_motivo || '').toString().trim();
      const tieneReemplazo = !!raw.reemplazo_id;
      return tieneMotivo && tieneReemplazo;
    }

    // Debe marcar la asistencia antes de poder guardar... salvo que haya escrito una
    // descripción (una novedad/observación se puede guardar sin marcar asistencia).
    const asistencia = (raw.estado_asistencia || '').toString().toUpperCase();
    const tieneDescripcion = !!(raw.descripcion || '').toString().trim();
    if (asistencia !== 'ASISTIO' && asistencia !== 'FALTO') {
      return tieneDescripcion;
    }

    if (asistencia === 'FALTO') {
      // FALTÓ normal: exige estado + reemplazo (salvo hueca pura o sacafranco).
      if (this.coberturaFaltoIncompleta) { return false; }
      // En fila normal, marcar "Hueca" y su motivo son OPCIONALES (no bloquean el guardado).
    }
    return true;
  }

  // Mensaje (tooltip) que explica por qué el botón está deshabilitado.
  get tituloGuardar(): string {
    if (this.guardando) { return ''; }
    if (this.esHuecaEstructural) {
      const raw = this.form?.getRawValue?.() || ({} as any);
      const faltaMotivo = !(raw.hueca_motivo || '').toString().trim();
      const faltaReemplazo = !raw.reemplazo_id;
      if (faltaMotivo || faltaReemplazo) {
        return 'HUECA: elige el motivo y el reemplazo (quién cubre)';
      }
      return '';
    }
    const asistencia = (this.form?.value?.estado_asistencia || '').toString().toUpperCase();
    const tieneDescripcion = !!(this.form?.value?.descripcion || '').toString().trim();
    if (asistencia !== 'ASISTIO' && asistencia !== 'FALTO' && !tieneDescripcion) {
      return 'Marca la asistencia (ASISTE o FALTÓ) o escribe una descripción';
    }
    if (asistencia === 'FALTO' && this.coberturaFaltoIncompleta) {
      return 'FALTÓ: elige el estado (cómo se cubrió) y el reemplazo';
    }
    return '';
  }

  get coberturaFaltoIncompleta(): boolean {
    // El sacafranco no requiere cobertura (estado/reemplazo) para marcar FALTO.
    if (this.esSacafranco) { return false; }
    const estadoAsistencia = (this.form?.value?.estado_asistencia || '').toString().toUpperCase();
    if (estadoAsistencia !== 'FALTO') { return false; }
    const estado = (this.form?.value?.estado || '').toString().trim().toUpperCase();
    const reemplazoId = this.form?.value?.reemplazo_id;
    const tieneEstadoReal = !!estado && estado !== 'TURNO';
    // HUECA sin estado de cobertura: falto sin reemplazo, se puede guardar (solo el motivo).
    if (this.form?.getRawValue().hueca && !tieneEstadoReal) { return false; }
    // En cualquier otro caso FALTO exige estado de cobertura Y reemplazo (aunque sea hueca).
    return !reemplazoId || !tieneEstadoReal;
  }

  guardar(): void {
    if (this.guardando || this.form.invalid) return;
    if (!this.data?.row?.asignacion_id && !this.data?.row?.sacafranco_fila_id) return;

    // getRawValue incluye los controles deshabilitados (estado/reemplazo cuando NO es FALTO).
    const raw = this.form.getRawValue();

    // Si la asistencia es FALTO, exigir estado de cobertura y reemplazo antes de guardar.
    // Excepción: HUECA SIN estado de cobertura (falto sin reemplazo) — ahí solo se pide motivo.
    const estadoAsistencia = (raw.estado_asistencia || '').toString().toUpperCase();
    if (estadoAsistencia === 'FALTO' && !this.esSacafranco) {
      const estado = (raw.estado || '').toString().trim().toUpperCase();
      const reemplazoId = raw.reemplazo_id;
      const tieneEstadoReal = !!estado && estado !== 'TURNO';
      const huecaPura = raw.hueca && !tieneEstadoReal;
      if (!huecaPura && (!reemplazoId || !tieneEstadoReal)) {
        Swal.fire({
          icon: 'warning',
          title: 'Completa la cobertura',
          text: 'Como la asistencia es FALTO, debes elegir el ESTADO (cómo se cubrió: ADICIONAL, DOBLA, etc.) y el REEMPLAZO (quién cubrió) antes de guardar.',
        });
        return;
      }
    }

    // HUECA: exige MOTIVO y REEMPLAZO (quién cubre) antes de guardar.
    if (this.esHuecaEstructural) {
      const faltaMotivo = !(raw.hueca_motivo || '').toString().trim();
      const faltaReemplazo = !(raw.reemplazo_id);
      if (faltaMotivo || faltaReemplazo) {
        Swal.fire({
          icon: 'warning',
          title: 'Completa la hueca',
          text: 'En una HUECA debes elegir el MOTIVO y el REEMPLAZO (quién cubre) antes de guardar.',
        });
        return;
      }
    }
    // En fila normal, marcar "Hueca" y su motivo son OPCIONALES: no se exige nada.

    const payload: any = {
      estado: raw.estado || null,
      estado_asistencia: raw.estado_asistencia || null,
      reemplazo_id: raw.reemplazo_id === '' ? null : raw.reemplazo_id,
      descripcion: raw.descripcion ? raw.descripcion.toString().toUpperCase() : null,
      hueca: !!raw.hueca,
      hueca_motivo: raw.hueca ? (raw.hueca_motivo || null) : null,
      fecha: this.data?.fecha || null
    };

    // HUECA estructural: la fila sigue como "HUECA"; el REEMPLAZO cubre. Sin estado ni
    // asistencia, sin persona_cobertura. No toca Asignaciones.
    if (this.esHuecaEstructural) {
      // Cualquier hueca conserva el Estado elegido (habilitado al elegir motivo); ese
      // estado define la sección en Reporte de Guardia (ADELANTOS/DOBLADAS/etc.).
      payload.estado = raw.estado || null;
      // La asistencia en huecas es OPCIONAL (solo FALTÓ); si se marcó, se conserva.
      payload.estado_asistencia = raw.estado_asistencia || null;
      payload.persona_cobertura_id = null;
      payload.hueca = true;
    }

    // MOVIMIENTO INTERNO (fila normal): el guardia que realmente cubrió ese día se guarda
    // como persona_cobertura, SOLO en el reporte de ese día (no cambia la asignación). Si
    // queda vacío, se limpia (vuelve a mostrar al titular).
    if (this.esFilaNormal) {
      payload.persona_cobertura_id = this.coberturaSel ?? null;
    }

    this.guardando = true;
    this.error = '';

    // SACAFRANCO: no tiene asignacion; se guarda por su fila en el endpoint de sacafranco.
    const obs = (!this.data.row.asignacion_id && this.data.row.sacafranco_fila_id)
      ? this.reporteSvc.updateSacafrancoAsistencia(this.data.row.sacafranco_fila_id!, payload as any)
      : this.reporteSvc.updateReporteAsistencia(this.data.row.asignacion_id!, payload);

    obs.subscribe({
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
