"use client";

import React, { useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Plus, Trash2, UserPlus, X, Save } from "lucide-react";
import type { Suspect, SuspectField } from "@/types";

// Default fields suggested for a suspect
const DEFAULT_FIELD_TEMPLATES = [
  { key: "Name", value: "" },
  { key: "Address", value: "" },
  { key: "Mobile Number", value: "" },
  { key: "Email", value: "" },
  { key: "Date of Birth", value: "" },
  { key: "Occupation", value: "" },
];

interface SuspectCardProps {
  suspect: Suspect;
  suspectIndex: number;
  onUpdate: (suspectId: string, fields: SuspectField[]) => void;
  onDelete: (suspectId: string) => void;
}

function SuspectCard({ suspect, suspectIndex, onUpdate, onDelete }: SuspectCardProps) {
  const [fields, setFields] = useState<SuspectField[]>(suspect.fields);
  const [isEditing, setIsEditing] = useState(false);

  const addField = (template?: { key: string; value: string }) => {
    const newField: SuspectField = {
      id: `field-${Date.now()}-${Math.random()}`,
      key: template?.key || "",
      value: template?.value || "",
    };
    const updatedFields = [...fields, newField];
    setFields(updatedFields);
    setIsEditing(true);
  };

  const updateField = (fieldId: string, updates: Partial<SuspectField>) => {
    const updatedFields = fields.map(field =>
      field.id === fieldId ? { ...field, ...updates } : field
    );
    setFields(updatedFields);
  };

  const removeField = (fieldId: string) => {
    const updatedFields = fields.filter(field => field.id !== fieldId);
    setFields(updatedFields);
  };

  const saveChanges = () => {
    // Only save fields that have both key and value
    const validFields = fields.filter(f => f.key.trim() && f.value.trim());
    onUpdate(suspect.id, validFields);
    setFields(validFields);
    setIsEditing(false);
  };

  const cancelChanges = () => {
    setFields(suspect.fields);
    setIsEditing(false);
  };

  const addDefaultFields = () => {
    const newFields = DEFAULT_FIELD_TEMPLATES.map(template => ({
      id: `field-${Date.now()}-${Math.random()}`,
      ...template,
    }));
    setFields([...fields, ...newFields]);
    setIsEditing(true);
  };

  return (
    <Card className="relative">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center gap-2">
              <span className="text-sm font-medium text-muted-foreground">Suspect #{suspectIndex + 1}</span>
              {suspect.fields.find(f => f.key.toLowerCase() === 'name')?.value && (
                <span className="text-base font-bold">
                  - {suspect.fields.find(f => f.key.toLowerCase() === 'name')?.value}
                </span>
              )}
            </CardTitle>
            <CardDescription>
              {fields.length} field(s) • Last updated: {new Date(suspect.updatedAt).toLocaleString()}
            </CardDescription>
          </div>
          <Button
            variant="destructive"
            size="sm"
            onClick={() => onDelete(suspect.id)}
            className="shrink-0"
          >
            <Trash2 className="h-4 w-4 mr-1" />
            Delete Suspect
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Fields List */}
        <div className="space-y-3">
          {fields.map((field, index) => (
            <div key={field.id} className="flex items-center gap-2">
              <div className="grid grid-cols-2 gap-2 flex-1">
                <div>
                  <Input
                    placeholder="Field name (e.g., Name)"
                    value={field.key}
                    onChange={(e) => updateField(field.id, { key: e.target.value })}
                    className="font-medium"
                  />
                </div>
                <div className="flex items-center gap-2">
                  <Input
                    placeholder="Value"
                    value={field.value}
                    onChange={(e) => updateField(field.id, { value: e.target.value })}
                  />
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => removeField(field.id)}
                    className="shrink-0"
                  >
                    <X className="h-4 w-4 text-red-500" />
                  </Button>
                </div>
              </div>
            </div>
          ))}

          {fields.length === 0 && (
            <div className="text-center py-8 text-muted-foreground">
              <p>No fields added yet. Add fields to record suspect details.</p>
            </div>
          )}
        </div>

        {/* Action Buttons */}
        <div className="flex flex-wrap gap-2 pt-4 border-t">
          <Button
            variant="outline"
            size="sm"
            onClick={() => addField()}
          >
            <Plus className="h-4 w-4 mr-1" />
            Add Custom Field
          </Button>
          
          {fields.length === 0 && (
            <Button
              variant="outline"
              size="sm"
              onClick={addDefaultFields}
            >
              <Plus className="h-4 w-4 mr-1" />
              Add Default Fields
            </Button>
          )}

          {isEditing && (
            <>
              <Button
                variant="default"
                size="sm"
                onClick={saveChanges}
              >
                <Save className="h-4 w-4 mr-1" />
                Save Changes
              </Button>
              <Button
                variant="ghost"
                size="sm"
                onClick={cancelChanges}
              >
                Cancel
              </Button>
            </>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

export function SuspectManagement({ 
  suspects, 
  onSuspectsChange 
}: {
  suspects: Suspect[]
  onSuspectsChange: (suspects: Suspect[]) => void
}) {
  const addSuspect = () => {
    const newSuspect: Suspect = {
      id: `suspect-${Date.now()}`,
      fields: [],
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    onSuspectsChange([...suspects, newSuspect]);
  };

  const updateSuspect = (suspectId: string, fields: SuspectField[]) => {
    onSuspectsChange(suspects.map(suspect =>
      suspect.id === suspectId
        ? { ...suspect, fields, updatedAt: new Date().toISOString() }
        : suspect
    ));
  };

  const deleteSuspect = (suspectId: string) => {
    onSuspectsChange(suspects.filter(suspect => suspect.id !== suspectId));
  };

  const exportData = () => {
    const dataStr = JSON.stringify({ suspects }, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `suspects-${Date.now()}.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const importData = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const data = JSON.parse(e.target?.result as string);
        if (data.suspects && Array.isArray(data.suspects)) {
          onSuspectsChange(data.suspects);
        }
      } catch (error) {
        console.error('Failed to import suspects:', error);
        alert('Failed to import file. Please ensure it\'s a valid JSON file.');
      }
    };
    reader.readAsText(file);
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Suspect Database</h2>
          <p className="text-muted-foreground">
            Manage suspect information with customizable fields
          </p>
        </div>
        <div className="flex gap-2">
          <input
            type="file"
            id="import-suspects"
            className="hidden"
            accept=".json"
            onChange={importData}
          />
          <Button
            variant="outline"
            onClick={() => document.getElementById('import-suspects')?.click()}
          >
            Import
          </Button>
          <Button
            variant="outline"
            onClick={exportData}
            disabled={suspects.length === 0}
          >
            Export
          </Button>
          <Button onClick={addSuspect}>
            <UserPlus className="h-4 w-4 mr-2" />
            Add Suspect
          </Button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-3">
            <CardDescription>Total Suspects</CardDescription>
            <CardTitle className="text-3xl">{suspects.length}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-3">
            <CardDescription>Total Fields</CardDescription>
            <CardTitle className="text-3xl">
              {suspects.reduce((sum, s) => sum + s.fields.length, 0)}
            </CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-3">
            <CardDescription>Last Updated</CardDescription>
            <CardTitle className="text-lg">
              {suspects.length > 0
                ? new Date(Math.max(...suspects.map(s => new Date(s.updatedAt).getTime()))).toLocaleString()
                : 'N/A'}
            </CardTitle>
          </CardHeader>
        </Card>
      </div>

      {/* Suspects List */}
      {suspects.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <UserPlus className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <h3 className="text-lg font-medium mb-2">No suspects added yet</h3>
            <p className="text-muted-foreground mb-4">
              Start by adding a suspect and filling in their details
            </p>
            <Button onClick={addSuspect}>
              <UserPlus className="h-4 w-4 mr-2" />
              Add Your First Suspect
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {suspects.map((suspect, index) => (
            <SuspectCard
              key={suspect.id}
              suspect={suspect}
              suspectIndex={index}
              onUpdate={updateSuspect}
              onDelete={deleteSuspect}
            />
          ))}
        </div>
      )}
    </div>
  );
}
